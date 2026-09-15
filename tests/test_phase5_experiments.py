"""Failure-sensitive checks for new disposable evaluators; no provider dispatch."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e1 = load('e1_evaluator_test', 'experiments/e1/evaluate.py')
e3 = load('e3_campaign_test', 'experiments/e3/campaign.py')


@pytest.fixture
def capsule(tmp_path):
    # Retained independent-command raw evidence is also a regression corpus for
    # the oracle. Each test corrupts a private copy, never the experiment receipt.
    source = ROOT / 'docs/receipts/phase5/e1-run-02/26'
    cell = tmp_path / 'cell'
    shutil.copytree(source, cell)
    return cell


def test_recovery_oracle_accepts_retained_independent_evidence(capsule):
    result = e1.oracle(capsule, e1.read(ROOT / 'experiments/e1/protocol.json'))
    assert result['completed_review'] and result['explicit_reconciliation']
    assert result['effects'] == 2


@pytest.mark.parametrize('fault', ['constraint', 'duplicate-effect', 'false-verification',
                                  'missing-guard', 'changed-corpus', 'checkpoint', 'correlation'])
def test_recovery_oracle_rejects_corrupted_evidence(capsule, fault):
    outcome = e1.read(capsule / 'outcome.json')
    if fault == 'constraint':
        outcome['accepted']['answers']['objective'] = 'Different task'
    elif fault == 'false-verification':
        outcome['document_outcome'] = 'refuted'
    elif fault == 'missing-guard':
        outcome['steps'] = [s for s in outcome['steps'] if s['action'] != 'transfer' or s['status'] != 'blocked']
    elif fault == 'duplicate-effect':
        ledger = capsule / 'effects.jsonl'
        ledger.write_text(ledger.read_text() + ledger.read_text().splitlines()[0] + '\n')
    elif fault == 'changed-corpus':
        (capsule / 'project/reference.md').write_text('Changed evidence')
    elif fault == 'checkpoint':
        record = e1.read(capsule / 'before.json')
        record['checkpoint_digest'] = 'wrong'
        e1.write(capsule / 'before.json', record)
    else:
        ledger = capsule / 'effects.jsonl'
        entries = [json.loads(line) for line in ledger.read_text().splitlines()]
        entries[0]['turn']['objective'] = 'Changed correlation'
        ledger.write_text('\n'.join(json.dumps(v) for v in entries) + '\n')
    e1.write(capsule / 'outcome.json', outcome)
    with pytest.raises(AssertionError):
        e1.oracle(capsule, e1.read(ROOT / 'experiments/e1/protocol.json'))


def test_e3_plan_is_complete_and_does_not_ship_answers():
    prepared = e3.plan()
    assert prepared == e3.plan()  # Stable randomized order.
    assert len(prepared['trials']) == len({t['trial_id'] for t in prepared['trials']}) == 144
    assert prepared['provider_calls'] == 0 and prepared['kind'] == 'prepared-only'
    assert all(set(t['input']) == {'id', 'family', 'prompt'} for t in prepared['trials'])
    assert len(prepared['blocked_on']) == 3


def test_synthetic_wrong_answers_are_detected_without_a_product_claim():
    report = e3.score(e3.synthetic())
    assert report['disposition'] == 'inconclusive'
    assert report['observed_product_cost_reduction'] is None
    for values in report['aggregates'].values():
        assert values['trials'] == 36 and values['completed_correct'] == 34
        assert values['critical_misses'] == 1
        assert values['false_alarms'] == 1


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'unknown', 'task-revision', 'protocol-revision',
                                  'real-claim', 'negative-cost', 'nan-cost', 'infinite-latency',
                                  'boolean-cost', 'unmeasured-repair', 'duplicate-finding', 'verdict', 'extra-output',
                                  'negative-tokens', 'boolean-tokens', 'fractional-tokens'])
def test_e3_rejects_incomplete_or_misleading_results(fault):
    results = e3.synthetic()
    first = results['trials'][0]
    if fault == 'missing': results['trials'].pop()
    elif fault == 'duplicate': results['trials'].append(first)
    elif fault == 'unknown': first['trial_id'] = 'unplanned'
    elif fault == 'task-revision': first['task_revision'] = 'old'
    elif fault == 'protocol-revision': results['protocol_revision'] = 'old'
    elif fault == 'real-claim': results['kind'] = 'live-model'
    elif fault == 'negative-cost': first['model_cost_usd'] = -1
    elif fault == 'nan-cost': first['model_cost_usd'] = float('nan')
    elif fault == 'infinite-latency': first['latency_seconds'] = float('inf')
    elif fault == 'boolean-cost': first['model_cost_usd'] = False
    elif fault == 'unmeasured-repair': first['human_repair_seconds'] = None
    elif fault == 'duplicate-finding': first['output']['findings'] = ['risk', 'risk']
    elif fault == 'verdict': first['output']['verdict'] = 'success'
    elif fault == 'negative-tokens': first['input_tokens'] = -1
    elif fault == 'boolean-tokens': first['input_tokens'] = False
    elif fault == 'fractional-tokens': first['output_tokens'] = 1.5
    else: first['output']['self_verified'] = True
    with pytest.raises(ValueError):
        e3.score(results)


def test_naming_a_critical_risk_while_claiming_readiness_is_still_a_miss():
    results = e3.synthetic()
    first = next(t for t in results['trials'] if t['trial_id'] == 'defect-03:solo:0')
    first['output']['findings'] = ['effect-before-grant']
    report = e3.score(results)
    assert report['aggregates']['solo']['critical_misses'] == 1


@pytest.mark.parametrize('signals,expected', [((False, False, False), 0), ((True, False, False), 1),
                                           ((False, True, False), 3), ((True, False, True), 3)])
def test_adaptive_route_uses_declared_signals_only(signals, expected):
    assert e3.adaptive_reviews(*signals) == expected


@pytest.mark.parametrize('signals', [(1, False, False), (False, False, True)])
def test_adaptive_route_rejects_unavailable_or_nonboolean_signals(signals):
    with pytest.raises(ValueError):
        e3.adaptive_reviews(*signals)
