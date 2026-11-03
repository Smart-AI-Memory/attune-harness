"""Funding requests derive from genuine accepted owners, not supplied prompts."""
# qualify: platform

import copy
import os

import pytest

from attune_harness import task_runtime
from attune_harness.recovery import RecoveryCursor, load_recovery, resume_review, transfer_lead
from attune_harness.review import prepare_review, review
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import RunStore
from attune_harness.task_contract import accept_task, read_task
from attune_harness.task_policies import (AssessmentPolicy, TaskExecutionStore, execute_task, prepare_task)

from test_review import case, change_config, scripted
from test_extensions import bundle, installed, extended
from test_openai_funding import api, registry_participant
from test_task_contract import draft, response
from test_task_repair import prepare as prepare_repair, proposal
from test_task_repair_effects import effect_case


def observe_builders(monkeypatch):
    """Compare actual dispatch inputs with independent owner reconstruction."""
    original = task_runtime.dispatch_assignment
    seen = []

    def dispatch(cursor, key, turn, config, exchange, outcome, **kwargs):
        if key not in cursor.events:
            cursor.begin(key, 'participant_turn', prepare_only=True,
                effect_class='read_only' if config['adapter'] == 'deterministic'
                and type(exchange) is ReviewExchange else 'unknown',
                participant_id=turn['participant_id'], attempt_id=turn['attempt_id'],
                turn_id=turn['turn_id'], request_digest=task_runtime.digest(turn))
        expected = task_runtime.funding_turn(cursor, cursor.events[key])
        assert expected == turn
        seen.append(copy.deepcopy(expected))
        return original(cursor, key, turn, config, exchange, outcome, **kwargs)

    monkeypatch.setattr(task_runtime, 'dispatch_assignment', dispatch)
    return seen


def test_legacy_history_and_budgets_reconstruct_all_turns(case, monkeypatch):
    seen = observe_builders(monkeypatch)
    completed = review(*case, allow_external=True)
    assert completed['status'] == 'completed' and len(seen) == 6
    assert [turn['remaining_tool_calls'] for turn in seen] == [2, 1, 0, 2, 1, 0]
    assert [len(turn['history']) for turn in seen] == [0, 1, 2, 0, 1, 2]


def test_extension_contracts_and_actions_reconstruct(extended, monkeypatch):
    seen = observe_builders(monkeypatch)
    assert review(*extended, allow_external=True)['status'] == 'completed'
    assert seen and all('evidence.search' in turn['tool_contracts'] for turn in seen)
    assert seen[1]['history'][0]['action']['name'] == 'evidence.search'


@pytest.mark.parametrize('result_profile', [None, 'assessment-findings-v1'])
def test_accepted_assessment_reuses_policy_turn(case, monkeypatch, result_profile):
    if result_profile:
        def transports(value):
            for item in value['participants'].values():
                item.update(adapter='command', command=['offline-fixture'], timeout=10)
        change_config(case, transports)
    draft(case, plan='independent-review', **({'result_profile': result_profile} if result_profile else {}))
    submission = response(case[2]); submission['permissions']['external'] = True
    accept_task(case[2], submission)
    seen = observe_builders(monkeypatch)
    # The structured result profile has its own substantive decoder; a fixture final
    # response is sufficient to compare both owner requests before that decoder.
    def final(packet):
        text = ('{"schema_version":1,"kind":"assessment-findings-v1","findings":[],"notes":["Fixture"]}'
                if result_profile else 'Fixture assessment')
        return {'kind': 'final', 'text': text}
    completed = execute_task(case[2], exchange_factory=scripted(final))
    assert completed['status'] == 'completed' and len(seen) == 2, completed['execution'].get('error')
    assert all(turn['remaining_tool_calls'] == 0 and turn['remaining_turns'] == 1 for turn in seen)
    assert all(len(turn['history']) == 2 and 'Acceptance criteria:' in turn['objective'] for turn in seen)
    assert seen[0].get('result_profile') == result_profile


def test_transfer_context_is_reconstructed_without_prior_lead_answers(case, monkeypatch):
    change_config(case, lambda value: value['participants'].update(
        gamma=copy.deepcopy(value['participants']['alpha'])))
    seen = observe_builders(monkeypatch)
    paused = review(*case, max_operations=3, allow_external=True)
    moved = transfer_lead(case[2], paused['checkpoint_digest'], 'gamma', 'Fixture transfer')
    completed = resume_review(case[2], case[0], case[1], moved['checkpoint_digest'], allow_external=True)
    assert completed['status'] == 'completed'
    continuation = next(turn for turn in seen if turn['participant_id'] == 'gamma')
    assert continuation['history'] == []
    assert continuation['continuation']['accepted_submission'] == completed['accepted']['submission']


@pytest.mark.skipif(os.name != 'posix', reason='POSIX repair fixture')
def test_worker_and_reviewer_repair_payloads_reconstruct(effect_case, monkeypatch):
    directory = prepare_repair(effect_case)
    seen = observe_builders(monkeypatch)
    completed = execute_task(directory, exchange_factory=scripted(proposal))
    assert completed['status'] == 'completed' and len(seen) == 2
    assert seen[0]['repair']['before_files'] == completed['request']['repair']['scope']['inputs']
    assert seen[1]['repair']['artifact_digest'] == completed['execution']['integration']['artifact_digest']
    assert seen[1]['repair']['after_probe']['passed'] is True


@pytest.mark.parametrize('owner', ['review', 'assessment'])
@pytest.mark.parametrize('field', ['objective', 'query', 'document', 'history', 'remaining_tool_calls', 'protocol'])
def test_altered_real_owner_turn_refuses_before_admission(case, api, owner, field):
    change_config(case, lambda value: value['participants'].update(alpha=registry_participant()))
    if owner == 'review':
        paused = review(*case, allow_external=True, max_operations=2)
    else:
        draft(case)
        value = response(case[2]); value['permissions']['external'] = True
        accept_task(case[2], value)
        paused = execute_task(case[2], max_operations=2)
    assert paused['status'] == 'paused' and api.calls == []
    store = RunStore(case[2], existing=True)
    with store.lease():
        if owner == 'review':
            run = load_recovery(store, paused['checkpoint_digest'])
            adapter, prepared, policy, role = store, prepare_review(case[0], case[1]), None, 'lead'
        else:
            task = read_task(case[2]); run = task['execution']
            adapter, prepared, policy, role = TaskExecutionStore(store, task), prepare_task(task), AssessmentPolicy(task), 'assessor'
        run['initial_retrieval'] = next(e['result'] for e in run['events'] if e['operation_key'] == 'retrieval')
        run['preflight_verification'] = next(e['result'] for e in run['events'] if e['operation_key'] == 'preflight')
        run['status'] = 'running'; adapter.save(run)
        assignment = run['recovery']['assignments'][role]
        config = run['registry']['participants'][assignment['participant_id']]
        history = ([] if policy is None else [
            {'action': {'kind': 'tool', 'name': 'retrieve', 'arguments':
                {'query': prepared['answers']['query'], 'k': 3}}, 'result': run['initial_retrieval']},
            {'action': {'kind': 'tool', 'name': 'verify', 'arguments': {}}, 'result': run['preflight_verification']}])
        turn = task_runtime.assessment_turn(run, prepared, role, 0, config, history, 0, {}, policy)
        turn[field] = ({'path': '/foreign', 'text': 'Foreign task'} if field == 'document'
                       else [{'injected': True}] if field == 'history'
                       else 9 if field == 'remaining_tool_calls' else 'Foreign task')
        cursor = RecoveryCursor(run, adapter)
        with pytest.raises(ValueError, match='accepted owner inputs'):
            task_runtime.dispatch_assignment(cursor, assignment['attempt_id'] + ':turn:0', turn,
                config, ReviewExchange(config, prepared['paths']['corpus']), {}, allow_api_spend=True)
        event = run['events'][-1]
        assert event['phase'] == 'prepared' and 'funding' not in event
        assert api.calls == []
