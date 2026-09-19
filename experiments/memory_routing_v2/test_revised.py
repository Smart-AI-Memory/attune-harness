"""Offline controls for the revised contract and routing experiment."""

from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from jsonschema import ValidationError

import contract_v2 as contract
import run_revised as runner

CASES = runner.cases()


def answer(case, outcome=None, preview=True):
    expected = case['expected']
    outcome = outcome or expected['outcome']
    facts = deepcopy(case['input']['record']['facts'])
    if outcome == 'update':
        for fact in facts:
            if 'texts' in expected:
                new = expected['texts'][fact['id']]
                if new != fact['text']:
                    fact['source_ids'] = ['S3']
                fact['text'] = new
            else:
                if fact['id'] in expected['limits']:
                    value = expected['limits'][fact['id']]
                    fact['text'] = f'{fact["id"]} has a maximum of {value} concurrent jobs.'
        if 'limits' in expected:
            for fact in facts:
                fact['source_ids'] = {'north': ['S1', 'S2', 'S4', 'S6'], 'south': ['S1', 'S3'],
                    'staging': ['S1', 'S5'], 'aggregate': ['S7'], 'migrations': ['S8']}[fact['id']]
    elif outcome != 'no_change' or not preview:
        facts = []
    return {'outcome': outcome, 'facts': facts, 'reason': 'Fixture reason',
            'evidence_ids': [case['input']['sources'][-1]['id']],
            'request': '' if outcome in ('update', 'no_change') else 'Describe the specific unresolved need'}


def normalize(case, value):
    bound = contract.capture(case)
    return contract.normalize(bound, value, 'typed', current_record=case['input']['record'], current_sources=case['input']['sources'])


def test_live_schema_excludes_model_version_and_host_advances_once():
    case = CASES[0]
    value = answer(case)
    assert 'version' not in json.dumps(contract.TYPED)
    result = normalize(case, value)
    assert result['version'] == 12 and case['input']['record']['version'] == 11
    value['record_version'] = 11
    with pytest.raises(ValidationError):
        normalize(case, value)


@pytest.mark.parametrize('preview', [True, False])
def test_no_change_allows_exact_snapshot_or_empty(preview):
    case = CASES[1]
    assert normalize(case, answer(case, preview=preview)) == case['input']['record']


@pytest.mark.parametrize('field', ['text', 'scope', 'source_ids', 'id'])
def test_no_change_rejects_altered_preview(field):
    case = CASES[1]
    value = answer(case)
    value['facts'][0][field] = ['S2'] if field == 'source_ids' else 'Changed'
    with pytest.raises(ValueError):
        normalize(case, value)


@pytest.mark.parametrize('kind', ['version', 'same_version_text', 'source_text'])
def test_capture_is_independent_and_rejects_current_state_drift(kind):
    case = deepcopy(CASES[0])
    bound = contract.capture(case)
    if kind == 'version':
        case['input']['record']['version'] += 1
    elif kind == 'same_version_text':
        case['input']['record']['facts'][0]['text'] = 'Concurrent change'
    else:
        case['input']['sources'][0]['text'] = 'Changed evidence'
    assert bound['input'] != case['input']
    with pytest.raises(contract.StaleInput):
        contract.normalize(bound, answer(CASES[0]), 'typed', current_record=case['input']['record'], current_sources=case['input']['sources'])


def test_inflight_record_change_stops_without_model_escalation():
    case = deepcopy(CASES[-1])
    calls = []
    def call(*args):
        calls.append(args)
        case['input']['record']['version'] += 1
        return {'value': answer(CASES[-1])}
    result = runner.execute_job(case, 'typed', call)
    assert len(calls) == 1 and result['action'] == 'stale_stop'


@pytest.mark.parametrize('index,action', [(4, 'await_evidence'), (5, 'await_decision')])
def test_missing_source_and_pending_choice_do_not_escalate(index, action):
    case = CASES[index]
    calls = []
    def call(role, model, prompt, schema):
        calls.append(model)
        return {'value': answer(case)}
    result = runner.execute_job(case, 'typed', call)
    assert calls == ['luna'] and result['action'] == action and not result['escalated']


def test_reasoning_escalates_once_with_original_evidence():
    case = CASES[-1]
    calls = []
    def call(role, model, prompt, schema):
        calls.append((role, model, prompt))
        return {'value': answer(case, 'needs_reasoning') if len(calls) == 1 else answer(case)}
    result = runner.execute_job(case, 'typed', call)
    assert [(r,m) for r,m,p in calls] == [('worker', 'luna'), ('escalation', 'astra')]
    assert calls[1][2]['sources'] == case['input']['sources']
    assert 'previous_attempt' in calls[1][2]
    assert result['action'] == 'proposal_ready'


def test_astra_unresolved_reasoning_cannot_bounce_back():
    case = CASES[-1]
    calls = []
    def call(*args):
        calls.append(args)
        return {'value': answer(case, 'needs_reasoning')}
    result = runner.execute_job(case, 'typed', call)
    assert len(calls) == 2 and result['action'] == 'unresolved_reasoning'


def test_known_multistep_flag_routes_directly_to_astra():
    case = deepcopy(CASES[-1])
    case['input']['signals']['multi_step'] = True
    calls = []
    def call(role, model, prompt, schema):
        calls.append(model)
        return {'value': answer(case)}
    result = runner.execute_job(case, 'typed', call)
    assert calls == ['astra'] and not result['escalated']


def test_coarse_need_for_review_adds_stronger_call():
    case = CASES[4]
    calls = []
    def call(role, model, prompt, schema):
        calls.append(model)
        return {'value': answer(case, 'needs_review' if len(calls) == 1 else None)}
    result = runner.execute_job(case, 'coarse', call)
    assert calls == ['luna', 'astra'] and result['action'] == 'await_evidence'


@pytest.mark.parametrize('alter', ['missing_request', 'unknown_evidence', 'need_with_facts', 'empty_update', 'scope_change'])
def test_invalid_proposals_are_rejected(alter):
    case = CASES[0]
    value = answer(case)
    if alter == 'missing_request':
        value.update(outcome='needs_reasoning', facts=[], request='')
    elif alter == 'unknown_evidence':
        value['evidence_ids'] = ['S999']
    elif alter == 'need_with_facts':
        value.update(outcome='needs_evidence', request='More information')
    elif alter == 'empty_update':
        value['facts'] = []
    else:
        value['facts'][0]['scope'] = 'other'
    with pytest.raises(ValueError):
        normalize(case, value)


def test_valid_shape_and_references_do_not_prove_disposition():
    case = CASES[-1]
    wrong = answer(case, 'needs_evidence')
    assert normalize(case, wrong) == case['input']['record']
    assert case['expected']['outcome'] == 'update'


@pytest.mark.parametrize('verdict,action', [('supported','proposal_ready'), ('unsupported','quarantined'), ('uncertain','quarantined'), ('malformed','quarantined')])
def test_sampled_audit_controls_candidate_disposition(verdict, action):
    case = CASES[0]
    result = runner.execute_job(case, 'revised', lambda *args: {'value': answer(case)})
    value = {'verdict': verdict, 'reason': 'Fixture', 'evidence_ids': ['S3']}
    audit = runner.sampled_audit(case, result, lambda *args: {'value': value})
    assert result['action'] == action
    assert audit['state'] == ('rejected' if verdict == 'malformed' else 'completed')


def test_record_changed_during_audit_is_not_released():
    case = deepcopy(CASES[0])
    result = runner.execute_job(case, 'revised', lambda *args: {'value': answer(case)})
    def call(*args):
        case['input']['record']['version'] += 1
        return {'value': {'verdict': 'supported', 'reason': 'Fixture', 'evidence_ids': ['S3']}}
    audit = runner.sampled_audit(case, result, call)
    assert result['action'] == 'stale_stop' and audit['state'] == 'stale'


def test_private_expectations_do_not_enter_worker_or_audit_prompt():
    for case in CASES:
        bound = contract.capture(case)
        for prompt in (contract.prompt(bound, 'typed'), contract.prompt(bound, 'coarse'),
                       contract.audit_prompt(bound, {'candidate': case['input']['record']})):
            assert 'expected' not in prompt and 'rubric' not in prompt
        changed = deepcopy(case)
        changed['expected'] = {'outcome': 'invented'}
        assert contract.prompt(bound, 'typed') == contract.prompt(contract.capture(changed), 'typed')


def test_schedule_and_sample_are_frozen_and_bounded():
    plan = runner.schedule()
    assert len(plan) == 17 and sum(p['arm'] in ('legacy','revised') for p in plan) == 8
    assert sum(p['case_id']+'-'+p['arm'] == runner.AUDIT_JOB for p in plan) == 1


def test_inherited_native_failure_stops_before_audit_or_next_job(tmp_path, monkeypatch):
    packet = {'max_native_calls':26, 'order':runner.schedule(), 'per_call_timeout':180,
              'campaign_timeout':1800, 'audit_job':runner.AUDIT_JOB}
    calls = []
    def fail(argv, prompt, **kwargs):
        calls.append(argv)
        return SimpleNamespace(
            stdout='', stderr='fixture failure', failure='nonzero_exit', returncode=1)
    monkeypatch.setattr(runner.previous, 'invoke', fail)
    trial = runner.Campaign(packet, tmp_path)
    with pytest.raises(RuntimeError):
        trial.run()
    assert len(calls) == 1 and trial.ledger['status'] == 'stopped'
    with pytest.raises(FileExistsError):
        runner.Campaign(packet, tmp_path)
