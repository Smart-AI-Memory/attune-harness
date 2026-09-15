"""Independent per-trial scoring and descriptive paired task-cluster resampling."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parents[2]
STRATEGIES = ('solo', 'fixed-cross-review', 'fixed-roundtable', 'adaptive')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def answer(value):
    return {'verdict': value['verdict'], 'findings': sorted(value['findings'])}


def summaries(rows):
    result = {}
    for strategy in STRATEGIES:
        selected = [row for row in rows if row['strategy'] == strategy]
        result[strategy] = {'trials': len(selected), 'completed_correct': sum(row['correct'] for row in selected),
            **{key: sum(row[key] for row in selected) for key in ('failed', 'critical_misses', 'false_alarms',
                'supported_findings', 'input_tokens', 'output_tokens', 'generation_requests')},
            'median_tokens': statistics.median(row['input_tokens'] + row['output_tokens'] for row in selected),
            'median_latency_seconds': statistics.median(row['elapsed_seconds'] for row in selected),
            'paid_api_cost_usd': 0, 'human_repair_seconds': None}
    return result


def comparison(summary):
    baseline = min(('fixed-cross-review', 'fixed-roundtable'), key=lambda key:
        (-summary[key]['completed_correct'], summary[key]['critical_misses'], key))
    candidate, fixed = summary['adaptive'], summary[baseline]
    return {'baseline': baseline, 'correct_difference': candidate['completed_correct'] - fixed['completed_correct'],
        'critical_miss_difference': candidate['critical_misses'] - fixed['critical_misses'],
        'token_reduction': 1 - candidate['median_tokens'] / fixed['median_tokens'] if fixed['median_tokens'] else None,
        'latency_reduction': 1 - candidate['median_latency_seconds'] / fixed['median_latency_seconds'] if fixed['median_latency_seconds'] else None,
        'paid_cost_reduction': None}


def bootstrap(rows, protocol):
    task_rows = {}
    family_tasks = {}
    for row in rows:
        task_rows.setdefault(row['task_id'], []).append(row)
        family_tasks.setdefault(row['family'], set()).add(row['task_id'])
    rng = random.Random(protocol['bootstrap']['seed'])
    distributions = {name: [] for name in ('correct_difference', 'critical_miss_difference', 'token_reduction', 'latency_reduction')}
    selected_baselines = Counter()
    for _ in range(protocol['bootstrap']['replicas']):
        selected = [task for family in sorted(family_tasks)
                    for task in rng.choices(sorted(family_tasks[family]), k=len(family_tasks[family]))]
        replicate = [row for task in selected for row in task_rows[task]]
        result = comparison(summaries(replicate))
        selected_baselines[result['baseline']] += 1
        for name in distributions:
            if result[name] is not None:
                distributions[name].append(result[name])
    intervals = {}
    for name, values in distributions.items():
        values.sort()
        intervals[name] = [values[int((len(values) - 1) * q)] for q in protocol['bootstrap']['interval']] if values else None
    return {'replicas': protocol['bootstrap']['replicas'], 'descriptive_95_percent_intervals': intervals,
            'baseline_selection_counts': dict(selected_baselines),
            'scope': 'Exploratory paired task clusters, stratified by family; not population or paid-cost guarantees'}


def analyze(directory):
    protocol, plan = read(directory / 'protocol.json'), read(directory / 'plan.json')
    key = read(ROOT / 'experiments/e3/answer-key.json')
    tasks = {t['id']: t for t in read(ROOT / 'experiments/e3/tasks.json')}
    assert len(plan) == 144 and len({t['trial_id'] for t in plan}) == 144
    assert Counter(t['strategy'] for t in plan) == Counter({s: 36 for s in STRATEGIES})
    for name, expected in read(ROOT / 'docs/receipts/e3-local/freeze.json')['sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    for name, expected in read(directory / 'sources.json').items():
        assert hashlib.sha256((directory / 'sources' / name).read_bytes()).hexdigest() == expected
    rows = []
    for index, trial in enumerate(plan):
        record = read(directory / f'{index:03}/record.json')
        assert record['trial'] == trial and trial['task_revision'] == digest(tasks[trial['task_id']])
        assert record['protocol_revision'] == digest(protocol) and record['kind'] == 'local-model'
        assert '/site-packages/attune_harness/' in record['harness_location']
        assert record['status'] in ('completed', 'failed') and not record['uncertain_generation']
        calls = record['calls']
        assert 1 <= len(calls) <= 5 and len({call['stage'] for call in calls}) == len(calls)
        assert calls[0]['stage'] == 'draft'
        inputs = outputs = generations = 0
        for call in calls:
            wire = json.loads(call['wire_request'])
            body = json.loads(wire['attempt']['task']['objective'])
            stage = call['stage']
            assert body['task'] == tasks[trial['task_id']]['prompt']
            assert body['instruction'] == protocol['stage_instructions']['review' if stage.startswith('review-') else stage]
            allowed_keys = {'instruction', 'task'} | ({'initial_draft'} if stage != 'draft' else set()) | ({'independent_reviews'} if stage == 'final' else set())
            assert set(body) == allowed_keys, 'Unexpected information in participant context'
            if stage != 'draft':
                assert body['initial_draft'] == calls[0]['response']
            if stage.startswith('review-'):
                assert 'independent_reviews' not in body, 'Peer reviews leaked to a reviewer'
            if stage == 'final':
                assert body['independent_reviews'] == [c['response'] for c in calls if c['stage'].startswith('review-')]
            seed = protocol['repeat_seeds'][trial['repeat']] + protocol['stage_seed_offsets'][stage]
            assert call['seed'] == seed
            request, raw = call['generation_request'], call['raw_generation']
            if request is not None:
                generations += 1
                assert request['model'] == protocol['model'] and request['options'] == {**protocol['settings'], 'seed': seed}
                assert request['system'] == protocol['system_prompt'] and json.loads(request['prompt']) == body
                assert request['stream'] is False
            if raw is not None:
                assert raw['model'] == protocol['model'] and type(raw['prompt_eval_count']) is int and type(raw['eval_count']) is int
                inputs += raw['prompt_eval_count']; outputs += raw['eval_count']
                if call['state'] == 'completed':
                    assert raw['done'] is True and raw['done_reason'] == 'stop'
                    assert json.loads(raw['response']) == call['response']
            else:
                assert request is None, 'Generation usage is unknown'
        if record['status'] == 'completed':
            draft = calls[0]['response']
            strategy = trial['strategy']
            if strategy == 'solo' or (strategy == 'adaptive' and not draft['uncertain'] and not draft['critical_risk']):
                expected_stages = ['draft']
            else:
                first = calls[1]['response']
                extra = strategy == 'fixed-roundtable' or (strategy == 'adaptive' and
                    (draft['critical_risk'] or first['disagree'] or answer(first) != answer(draft)))
                expected_stages = ['draft', 'review-1', *(['review-2', 'review-3'] if extra else []), 'final']
            assert [c['stage'] for c in calls] == expected_stages
            assert all(c['state'] == 'completed' for c in calls)
            output = record['output']
            assert output == answer(calls[-1]['response'])
        else:
            assert record['output'] is None and calls[-1]['state'] == 'failed'
            output = None
        target = key[trial['task_id']]
        findings = set(output['findings']) if output else set()
        correct = output is not None and output['verdict'] == target['verdict'] and findings == set(target['findings'])
        critical = len(target['critical']) if output is None or output['verdict'] == 'ready' else len(set(target['critical']) - findings)
        rows.append({'trial_id': trial['trial_id'], 'task_id': trial['task_id'], 'family': trial['input']['family'],
            'strategy': trial['strategy'], 'repeat': trial['repeat'], 'correct': correct,
            'failed': record['status'] == 'failed', 'critical_misses': critical,
            'supported_findings': len(findings & set(target['findings'])), 'false_alarms': len(findings - set(target['findings'])),
            'input_tokens': inputs, 'output_tokens': outputs, 'generation_requests': generations,
            'elapsed_seconds': record['elapsed_seconds'], 'output': output})
    summary = summaries(rows)
    result = comparison(summary)
    disposition = 'revise' if result['correct_difference'] < 0 or result['critical_miss_difference'] > 0 else 'inconclusive'
    return {'experiment': 'E3-local-model', 'trials': len(rows), 'aggregates': summary, 'comparison': result,
        'uncertainty': bootstrap(rows, protocol), 'rows': rows, 'disposition': disposition,
        'paid_api_cost_usd': 0, 'human_interventions': 0, 'human_repair_seconds': None,
        'local_compute_cost_usd': None, 'scope': protocol['generalization']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.directory.resolve())
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))
