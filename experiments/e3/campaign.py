"""Offline E3 preparation/scoring. No model dispatch or credential access."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def frozen_inputs():
    freeze = read(ROOT / 'docs/receipts/phase5/e3-freeze.json')
    for name, expected in freeze['sha256'].items():
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen evaluation input changed: ' + name)
    protocol, tasks, answers = (read(HERE / name) for name in ('protocol.json', 'tasks.json', 'answer-key.json'))
    ids = [task['id'] for task in tasks]
    if len(set(ids)) != 12 or len(ids) != 12 or set(ids) != set(answers):
        raise ValueError('Expected twelve unique tasks with separate answers')
    if Counter(t['family'] for t in tasks) != Counter({f: 3 for f in protocol['families']}):
        raise ValueError('Expected three tasks in each family')
    if set(ids) & set(protocol['tuning_tasks']):
        raise ValueError('Tuning and evaluation tasks overlap')
    return protocol, tasks, answers


def plan():
    protocol, tasks, _ = frozen_inputs()
    trials = []
    for task in tasks:
        for strategy in protocol['strategies']:
            for repeat in range(protocol['repeats']):
                trials.append({'trial_id': f'{task["id"]}:{strategy}:{repeat}', 'task_id': task['id'],
                    'task_revision': digest(task), 'strategy': strategy, 'repeat': repeat, 'input': task,
                    'output_contract': protocol['output_contract'], 'strategy_protocol': protocol['strategies'][strategy]})
    random.Random(protocol['order_seed']).shuffle(trials)
    return {'experiment': 'E3', 'protocol_revision': digest(protocol), 'kind': 'prepared-only',
            'provider_calls': 0, 'trials': trials, 'blocked_on':
            ['exact model bindings and settings', 'priced plan and explicit spend authorization',
             'qualified strategy execution and task-cluster uncertainty analysis']}


def adaptive_reviews(uncertain, critical_risk, disagreement=False):
    """Declared signals choose consultation count; they do not verify model claims."""
    if any(type(value) is not bool for value in (uncertain, critical_risk, disagreement)):
        raise ValueError('Routing signals must be booleans')
    if disagreement and not (uncertain or critical_risk):
        raise ValueError('No review was requested; disagreement is not an available signal')
    return 3 if critical_risk or disagreement else 1 if uncertain else 0


def nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(name + ' must be finite, nonnegative measured data')
    return value


def score(results):
    protocol, _, answers = frozen_inputs()
    prepared = plan()
    if results.get('kind') != 'synthetic-validation':
        raise ValueError('Only synthetic validation is supported until real execution is qualified')
    if results.get('protocol_revision') != prepared['protocol_revision']:
        raise ValueError('Protocol revision mismatch')
    expected = {trial['trial_id']: trial for trial in prepared['trials']}
    seen, rows = set(), []
    for result in results['trials']:
        trial_id = result['trial_id']
        if trial_id not in expected or trial_id in seen:
            raise ValueError('Unknown or duplicate trial')
        seen.add(trial_id)
        trial = expected[trial_id]
        if result['task_revision'] != trial['task_revision']:
            raise ValueError('Task revision mismatch')
        output = result['output']
        if set(output) != {'verdict', 'findings'} or output['verdict'] not in ('ready', 'revise', 'blocked'):
            raise ValueError('Invalid structured output')
        findings = output['findings']
        if (not isinstance(findings, list) or any(not isinstance(f, str) or not f for f in findings)
                or len(set(findings)) != len(findings)):
            raise ValueError('Findings must be unique strings')
        answer = answers[trial['task_id']]
        correct = output['verdict'] == answer['verdict'] and set(findings) == set(answer['findings'])
        missing = set(answer['critical']) - set(findings)
        # Merely naming a critical risk while declaring readiness still misses it.
        critical_misses = len(missing) if output['verdict'] != 'ready' else len(answer['critical'])
        tokens = {}
        for name in ('input_tokens', 'output_tokens'):
            if type(result[name]) is not int or result[name] < 0:
                raise ValueError(name + ' must be a nonnegative integer')
            tokens[name] = result[name]
        rows.append({'trial_id': trial_id, 'strategy': trial['strategy'], 'task_id': trial['task_id'],
            'completed_correct': correct, 'critical_misses': critical_misses,
            'supported_findings': len(set(findings) & set(answer['findings'])),
            'false_alarms': len(set(findings) - set(answer['findings'])), **tokens,
            **{name: nonnegative(result[name], name) for name in
               ('model_cost_usd', 'latency_seconds', 'human_repair_seconds')}})
    if seen != set(expected):
        raise ValueError('Incomplete 144-trial matrix')
    aggregates = {}
    for strategy in protocol['strategies']:
        subset = [row for row in rows if row['strategy'] == strategy]
        aggregates[strategy] = {'trials': len(subset),
            'completed_correct': sum(row['completed_correct'] for row in subset),
            'critical_misses': sum(row['critical_misses'] for row in subset),
            **{name: sum(row[name] for row in subset) for name in
               ('supported_findings', 'false_alarms', 'input_tokens', 'output_tokens')},
            **{'median_' + name: statistics.median(row[name] for row in subset)
               for name in ('model_cost_usd', 'latency_seconds', 'human_repair_seconds')}}
    return {'experiment': 'E3', 'kind': 'synthetic-validation', 'trials': len(rows), 'aggregates': aggregates,
            'rows': rows, 'disposition': 'inconclusive', 'observed_product_cost_reduction': None,
            'uncertainty_analysis': 'not run; synthetic values cannot establish product value', 'provider_calls': 0}


def synthetic():
    """A scorer fixture, deliberately includes wrong answers; never quality evidence."""
    prepared = plan()
    _, _, answers = frozen_inputs()
    results = {'kind': 'synthetic-validation', 'protocol_revision': prepared['protocol_revision'], 'trials': []}
    for trial in prepared['trials']:
        answer = answers[trial['task_id']]
        output = {'verdict': answer['verdict'], 'findings': list(answer['findings'])}
        # One critical miss per strategy on repeat zero exercises negative scoring.
        if trial['task_id'] == 'defect-03' and trial['repeat'] == 0:
            output = {'verdict': 'ready', 'findings': []}
        if trial['task_id'] == 'clean-01' and trial['repeat'] == 0:
            output = {'verdict': 'revise', 'findings': ['invented-defect']}
        results['trials'].append({'trial_id': trial['trial_id'], 'task_revision': trial['task_revision'],
            'output': output, 'model_cost_usd': 0, 'latency_seconds': 0, 'human_repair_seconds': 0,
            'input_tokens': 0, 'output_tokens': 0})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'validate-synthetic'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir()  # Preserve every prior campaign/validation result.
    (args.output / 'sources').mkdir()
    sources = {}
    for name in ('campaign.py', 'protocol.json', 'tasks.json', 'answer-key.json'):
        source = HERE / name
        (args.output / 'sources' / name).write_bytes(source.read_bytes())
        sources[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    write(args.output / 'sources.json', sources)
    write(args.output / 'plan.json', plan())
    if args.action == 'validate-synthetic':
        results = synthetic()
        write(args.output / 'synthetic-results.json', results)
        report = score(results)
        write(args.output / 'synthetic-score.json', report)
        print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))
    else:
        print('Prepared 144 trial envelopes. No model calls; bindings and approval outstanding.')
