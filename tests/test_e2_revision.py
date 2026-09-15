"""Adversarial checks for the call-bound replacement; original E2 stays frozen."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('e2_call_bound_tests', ROOT / 'experiments/e2_revision/policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


@pytest.fixture(params=['00', '12'])
def invocation(request):
    # Raw independent command/MCP observations from the retained original experiment.
    cell = ROOT / 'docs/receipts/e2/run-01' / request.param
    current = json.loads((cell / 'current.json').read_text())
    raw = json.loads((cell / 'oracle.json').read_text())
    historical = policy.observation(current, raw['target_result'])
    decision = policy.plan(current, historical, cell / 'oracle-run')
    return current, raw, historical, decision


def test_working_call_returns_its_result_without_general_availability(invocation):
    current, raw, _, decision = invocation
    assert decision['status'] == 'invoke' and decision['history_status'] == 'matching_success'
    assert not decision['predicted_usable'] and not decision['verified_availability_claim']
    result = policy.finish(decision, current, current, raw)
    assert result['status'] == 'observed_success' and result['result'] == raw['target_result']
    assert result['availability'] == 'unverified' and not result['verified_availability_claim']


def test_success_history_cannot_hide_the_next_failure(invocation):
    current, raw, historical, decision = invocation
    failed = {'target_result': None, 'error': 'runtime failed'}
    result = policy.finish(decision, current, current, failed)
    assert result['status'] == 'observed_failure' and result['result'] is None and result['observation'] is None
    assert historical['result'] == raw['target_result']  # History is preserved, not promoted.


def test_previous_success_record_cannot_be_substituted_for_new_invocation(invocation):
    current, raw, historical, _ = invocation
    decision = policy.plan(current, historical, Path(raw['record']['record_path']).parent / 'another-call')
    assert policy.finish(decision, current, current, raw)['status'] == 'invalid_evidence'


@pytest.mark.parametrize('field,value', [('lifecycle', 'disabled'), ('grants', []), ('declared_tools', [])])
def test_current_denials_override_matching_history(invocation, field, value):
    current, raw, historical, decision = invocation
    current[field] = value
    denied = policy.plan(current, historical, Path(decision['record_path']).parent)
    assert denied['status'] == 'denied' and not denied['invocation_allowed']
    result = policy.finish(denied, current, current, raw)
    assert result['status'] == 'not_invoked' and result['result'] is None


def test_missing_dependency_does_not_reuse_success(invocation):
    current, _, historical, decision = invocation
    current['dependencies']['attune-rag'] = None
    assert policy.plan(current, historical, Path(decision['record_path']).parent)['status'] == 'unavailable'


@pytest.mark.parametrize('fault', ['absent', 'seal', 'empty-sources', 'malformed', 'nan', 'boolean-k'])
def test_missing_or_invalid_history_does_not_block_a_new_authorized_attempt(invocation, fault):
    current, _, historical, decision = invocation
    if fault == 'absent': historical = None
    elif fault == 'seal': historical['digest'] = 'wrong'
    elif fault == 'empty-sources': historical['result']['sources'] = []
    elif fault == 'malformed': historical = [None]
    elif fault == 'nan': historical['result']['k'] = float('nan')
    else: historical['result']['k'] = True
    result = policy.plan(current, historical, Path(decision['record_path']).parent)
    assert result['invocation_allowed'] and result['history_status'] in ('absent', 'invalid')
    assert not result['predicted_usable'] and not result['verified_availability_claim']


def test_upgraded_history_is_stale_but_new_operation_is_permitted(invocation):
    current, _, historical, decision = invocation
    current['artifact'] = {'digest': 'new', 'version': '0.2.0'}
    result = policy.plan(current, historical, Path(decision['record_path']).parent)
    assert result['history_status'] == 'stale' and result['invocation_allowed']


@pytest.mark.parametrize('when', ['before', 'after'])
def test_changed_scope_refuses_success(invocation, when):
    current, raw, _, decision = invocation
    changed = copy.deepcopy(current)
    changed['grants'] = []
    before, after = (changed, current) if when == 'before' else (current, changed)
    assert policy.finish(decision, before, after, raw)['status'] == 'scope_changed'


@pytest.mark.parametrize('fault', ['record-path', 'event-result', 'event-state', 'target-result', 'missing-record', 'duplicate-event'])
def test_call_correlation_and_actual_event_must_agree(invocation, fault):
    current, raw, _, decision = invocation
    events = raw['record']['events']
    target = next((event for event in events if event.get('action', {}).get('name') == 'evidence.search'), events[0])
    if fault == 'record-path': raw['record']['record_path'] += '.other'
    elif fault == 'event-result': target['result']['request_id'] = 'another-call'
    elif fault == 'event-state': target['state'] = 'failed'
    elif fault == 'target-result': raw['target_result']['query'] = 'other query'
    elif fault == 'missing-record': raw.pop('record')
    else: events.append(copy.deepcopy(target))
    result = policy.finish(decision, current, current, raw)
    assert result['status'] == 'invalid_evidence' and result['result'] is None
