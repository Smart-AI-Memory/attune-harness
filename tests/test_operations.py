import copy
import json

import pytest

from attune_harness.cli import main
from attune_harness.operations import repair_economics, triage


def event(**changes):
    return dict(repository='fixture', revision='abc', check='tests', run_id='1',
                status='failed', failure_kind='test', effects='none', attempts=0, **changes)


def ledger():
    return {'schema_version': 1, 'scope': 'synthetic', 'quality_floor': {
        'minimum_verified_repairs': 1, 'max_critical_misses': 0, 'max_unsupported_assertions': 0},
        'attempts': [{'attempt_id': 'a', 'repair_id': 'r', 'strategy': 'sol-first', 'model': 'sol',
            'stage': 'initial', 'outcome': 'failed',
            'verification': {'independent': True, 'passed': False, 'evidence_sha256': '1'*64},
            'input_tokens': 10, 'output_tokens': 5, 'reasoning_output_tokens': 3,
            'model_cost_usd': 1, 'verification_cost_usd': 0.5,
            'human_minutes': 3, 'human_hourly_usd': 60, 'critical_misses': 0, 'unsupported_assertions': 0},
        {'attempt_id': 'b', 'repair_id': 'r', 'strategy': 'sol-first', 'model': 'astra',
            'stage': 'escalation', 'outcome': 'verified',
            'verification': {'independent': True, 'passed': True, 'evidence_sha256': '2'*64},
            'input_tokens': 20, 'output_tokens': 10, 'reasoning_output_tokens': 4,
            'model_cost_usd': 2, 'verification_cost_usd': 0.5,
            'human_minutes': 0, 'human_hourly_usd': 60, 'critical_misses': 0, 'unsupported_assertions': 0}]}


@pytest.mark.parametrize('status,expected', [('pending','wait'),('passed','observe'),
    ('cancelled','human_review'),('unknown','human_review'),('failed','propose_repair_team')])
def test_trusted_status_determines_suggestion(status, expected):
    e=event();e['status']=status
    r=triage(e)
    assert r['action']==expected and not r['dispatch_authorized']


def test_storm_key_spans_runs_but_not_revisions():
    e=event();key=triage(e)['key'];e['run_id']='2'
    assert triage(e,handled_keys=[key])['action']=='duplicate'
    e['revision']='def'
    assert triage(e,handled_keys=[key])['action']=='propose_repair_team'
    e['attempts']=2
    assert triage(e)['action']=='human_review'
    e['effects']='unknown';e['status']='passed'
    assert triage(e)['action']=='reconcile'


def test_infrastructure_is_not_a_code_repair():
    e=event();e['failure_kind']='infrastructure'
    assert triage(e)['action']=='propose_infrastructure_review'


def test_all_attempts_and_human_correction_count_once():
    r=repair_economics(ledger());s=r['strategies'][0]
    assert s['verified_repairs']==1 and s['attempts']==2
    assert s['cost_per_verified_repair_usd']==7
    assert s['output_tokens']==15 and s['reasoning_output_tokens']==7
    assert r['eligible_cost_ranking']==['sol-first']


@pytest.mark.parametrize('field',['model_cost_usd','verification_cost_usd','human_minutes','human_hourly_usd'])
def test_missing_evidence_prevents_price_ranking(field):
    x=ledger();x['attempts'][0][field]=None
    r=repair_economics(x)
    assert r['eligible_cost_ranking']==[]
    assert r['strategies'][0]['total_cost_usd'] is None


@pytest.mark.parametrize('field',['critical_misses','unsupported_assertions'])
def test_quality_blocks_even_free_work(field):
    x=ledger();x['attempts'][0][field]=1
    assert not repair_economics(x)['eligible_cost_ranking']


@pytest.mark.parametrize('mutation', ['duplicate','self_verified','no_evidence','bool_tokens',
    'negative_cost','nan_cost','double_reasoning','strategy_swap','no_initial','after_verified'])
def test_bad_ledger_rejected(mutation):
    x=ledger();a,b=x['attempts']
    if mutation=='duplicate':b['attempt_id']=a['attempt_id']
    if mutation=='self_verified':b['verification']['independent']=False
    if mutation=='no_evidence':b['verification']['evidence_sha256']=None
    if mutation=='bool_tokens':a['input_tokens']=True
    if mutation=='negative_cost':a['model_cost_usd']=-1
    if mutation=='nan_cost':a['human_minutes']=float('nan')
    if mutation=='double_reasoning':a['reasoning_output_tokens']=9
    if mutation=='strategy_swap':b['strategy']='astra-only'
    if mutation=='no_initial':a['stage']='retry'
    if mutation=='after_verified':x['attempts'].append({**copy.deepcopy(b),'attempt_id':'c','stage':'retry'})
    with pytest.raises(ValueError):repair_economics(x)


def test_cli_never_dispatches(tmp_path,capsys):
    p=tmp_path/'event.json';p.write_text(json.dumps({'event':event(),'handled_keys':[],'max_attempts':2}),encoding='utf-8')
    assert main(['triage-check',str(p)])==0
    assert json.loads(capsys.readouterr().out)['dispatch_authorized'] is False
    p.write_text(json.dumps(ledger()),encoding='utf-8')
    assert main(['repair-economics',str(p)])==0
    assert json.loads(capsys.readouterr().out)['strategies'][0]['verified_repairs']==1
