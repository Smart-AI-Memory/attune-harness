"""Funded planning/build journeys use real owners and inert API responses."""
# qualify: platform

import copy
import importlib
import json
import os

import pytest

from attune_harness.cli import main
from attune_harness.process import ProcessResult
from attune_harness.review_contract import canonical, digest
from attune_harness.review_store import RunStore, read_record
from attune_harness.task_contract import read_task
from attune_harness.task_policies import execute_task
from attune_harness.work_runtime import demonstration_reply, plan_work
from test_work_build import prepare as prepare_build, Worker
from test_work_contract import make, work
from test_work_planning import add_critic


KEY_NAME = 'HARNESS_WORK_PROFILE_TEST_KEY'
KEY = 'synthetic_work_key_0123456789abcdefghijkl'


def funded_registry(work):
    value = json.loads(work[1].read_text(encoding='utf-8'))
    for name in ('local', 'critic'):
        value['participants'][name] = {
            'adapter': 'openai', 'model': 'fixture-work-model-' + name, 'timeout': 10,
            'tools': [], 'max_turns': 1, 'max_tool_calls': 0,
            'funding': {'mode': 'api', 'credential_env': KEY_NAME},
        }
    work[1].write_text(canonical(value), encoding='utf-8')


class WorkAPI:
    def __init__(self):
        self.owner = None
        self.calls = []

    def __call__(self, argv, raw, **kwargs):
        body = json.loads(raw)['body']
        attempt = json.loads(body['input'].split('\n', 1)[1])['attempt']
        turn = json.loads(attempt['task']['objective'])
        assert body['tools'] == [] and body['store'] is False
        assert kwargs['environment']['OPENAI_API_KEY'] == KEY
        assert KEY_NAME not in kwargs['environment']
        profile = attempt['adapter_version']
        phase = 'planning' if profile == 'feature-planning-v1' else 'build'
        assert profile in ('feature-planning-v1', 'feature-build-v1')
        saved = read_record(self.owner)
        event = next(event for event in saved[phase]['events']
                     if event.get('turn_id') == turn['turn_id'])
        selected = saved['request']['registry']['participants'][turn['participant_id']]
        assert event['phase'] == 'dispatching'
        assert event['funding']['state'] == 'matched'
        assert event['funding']['api_authorized'] is True
        assert event['funding']['configuration_digest'] == digest(selected)
        assert event['funding']['attempt_id'] == turn['turn_id']
        assert event['funding']['request_digest'] == digest(turn)
        if phase == 'planning':
            payload = demonstration_reply(turn)
        else:
            # Reuse the established file/check fixture, returning only its
            # substantive contract. The real owner reconstructs control data.
            fixture = Worker(selected, kwargs['cwd'], profile=profile)
            wire = canonical({'turn': turn, 'request_digest': digest(turn)})
            payload = json.loads(json.loads(fixture(wire))['action']['text'])
            if turn['role'] == 'worker':
                payload = {'schema_version': 2, 'files': payload['files']}
        assert not ({'request_digest', 'action', 'attempt_id', 'dependencies', 'task_id'} & payload.keys())
        self.calls.append({'turn': copy.deepcopy(turn), 'payload': copy.deepcopy(payload)})
        output = {
            'id': 'resp_work_fixture_' + str(len(self.calls)), 'status': 'completed', 'model': body['model'],
            'error': None, 'incomplete_details': None,
            'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                        'content': [{'type': 'output_text', 'text': canonical({'text': canonical(payload)})}]}],
            'usage': {'input_tokens': 17, 'output_tokens': 11,
                      'input_tokens_details': {'cached_tokens': 4}},
        }
        return ProcessResult(tuple(argv), 0, canonical(output), '')


@pytest.fixture
def api(monkeypatch):
    module = importlib.import_module('attune_harness.openai_exchange')
    monkeypatch.setenv(KEY_NAME, KEY)
    monkeypatch.setattr(Worker, 'mutation', None)
    monkeypatch.setattr(Worker, 'seen', [])
    transport = WorkAPI()
    monkeypatch.setattr(module, 'invoke', transport)
    participants = importlib.import_module('attune_harness.review_participants')
    monkeypatch.setattr(participants, 'invoke', lambda *args, **kwargs: pytest.fail('Unexpected command participant'))
    return transport


def assert_funded(run, count):
    events = [event for event in run['events'] if event['kind'] == 'participant_turn']
    assert len(events) == count
    for event in events:
        assert event['funding']['dispatch_outcome'] == 'completed'
        identity = event['result']['identity']
        assert identity['adapter'] == 'openai' and identity['funding'] == event['funding']
        assert identity['usage']['state'] == 'reported'
        assert (identity['usage']['input_tokens'], identity['usage']['output_tokens']) == (17, 11)
        assert identity['usage']['billed_cost_usd'] is None
        assert identity['usage']['remaining_balance'] is None
    assert run['permissions'] == {'external': True, 'native': False}


def status_is_inert_and_readable(directory, api, capsys):
    before = (directory / 'record.json').read_bytes()
    calls = len(api.calls)
    assert main(['status', str(directory), '--format', 'markdown']) == 0
    shown = capsys.readouterr().out
    assert 'Funding and usage' in shown
    assert 'api requested; api observed; matched' in shown
    assert 'input 17, output 11' in shown
    assert 'Billed cost and remaining balance: unknown' in shown
    assert KEY not in shown
    assert len(api.calls) == calls and (directory / 'record.json').read_bytes() == before


def test_openai_planning_uses_real_owner_and_substantive_payload_with_durable_admission(work, api, capsys):
    funded_registry(work)
    add_critic(work)
    make(work)
    api.owner = work[2]['directory']
    completed = execute_task(api.owner, allow_external=True, allow_api_spend=True)
    assert completed['planning']['status'] == 'completed', completed['planning'].get('error')
    assert [call['turn']['role'] for call in api.calls] == ['planner', 'critic']
    assert api.calls[1]['turn']['proposal'] == api.calls[0]['payload']
    assert canonical(completed) == canonical(read_task(api.owner))
    assert_funded(completed['planning'], 2)
    status_is_inert_and_readable(api.owner, api, capsys)
    replayed = plan_work(api.owner, allow_external=True)
    assert canonical(replayed) == canonical(completed)
    assert len(api.calls) == 2


def test_openai_planning_pause_and_resume_replays_completed_calls_without_spending_again(work, api):
    funded_registry(work)
    add_critic(work)
    make(work)
    api.owner = work[2]['directory']
    paused = plan_work(api.owner, allow_external=True, allow_api_spend=True, max_operations=1)
    assert paused['planning']['status'] == 'paused' and len(api.calls) == 1
    completed = plan_work(api.owner, allow_external=True, allow_api_spend=True)
    assert completed['planning']['status'] == 'completed', completed['planning'].get('error')
    assert len(api.calls) == 2
    assert_funded(completed['planning'], 2)
    assert canonical(completed) == canonical(read_task(api.owner))


def test_openai_planning_missing_resume_authority_remains_prepared_then_accepts_fresh_grant(work, api):
    funded_registry(work)
    add_critic(work)
    make(work)
    api.owner = work[2]['directory']
    plan_work(api.owner, allow_external=True, allow_api_spend=True, max_operations=1)
    refused = plan_work(api.owner, allow_external=True)
    assert len(api.calls) == 1
    event = refused['planning']['events'][-1]
    assert event['phase'] == 'prepared'
    assert event['funding']['api_authorized'] is False
    assert event['funding']['dispatch_outcome'] == 'not_started'
    completed = plan_work(api.owner, allow_external=True, allow_api_spend=True)
    assert completed['planning']['status'] == 'completed', completed['planning'].get('error')
    assert len(api.calls) == 2
    assert completed['planning']['events'][-1]['funding_history'][0]['api_authorized'] is False


@pytest.mark.skipif(os.name != 'posix', reason='POSIX build profile only')
def test_openai_build_uses_real_owner_file_effects_and_acceptance_checks(work, api, capsys):
    funded_registry(work)
    root, directory, _ = prepare_build(work)
    api.owner = directory
    completed = execute_task(directory, allow_external=True, allow_api_spend=True)
    assert completed['build']['status'] == 'completed', completed['build'].get('error')
    assert [call['turn']['role'] for call in api.calls] == ['worker', 'worker', 'reviewer']
    assert_funded(completed['build'], 3)
    assert (root / 'pkg/export.py').read_text() == 'def answer():\n    return 42\n'
    assert (root / 'source.py').read_text() == 'from pkg.export import answer\ndef value():\n    return answer()\n'
    assert any(event['kind'] == 'file_effect' for event in completed['build']['events'])
    probes = [event for event in completed['build']['events'] if event['kind'] == 'acceptance_probe']
    assert probes and all(event['result']['passed'] for event in probes)
    assert canonical(completed) == canonical(read_task(directory))
    status_is_inert_and_readable(directory, api, capsys)
    replayed = execute_task(directory, allow_external=True)
    assert canonical(replayed) == canonical(completed)
    assert len(api.calls) == 3


@pytest.mark.skipif(os.name != 'posix', reason='POSIX build profile only')
def test_openai_build_pause_resume_replays_one_api_result_and_preserves_checked_files(work, api):
    funded_registry(work)
    _, directory, _ = prepare_build(work)
    api.owner = directory
    paused = execute_task(directory, allow_external=True, allow_api_spend=True, max_operations=2)
    assert paused['build']['status'] == 'paused' and len(api.calls) == 1
    completed = execute_task(directory, allow_external=True, allow_api_spend=True)
    assert completed['build']['status'] == 'completed', completed['build'].get('error')
    assert len(api.calls) == 3
    assert_funded(completed['build'], 3)
    assert canonical(completed) == canonical(read_task(directory))


@pytest.mark.skipif(os.name != 'posix', reason='POSIX build profile only')
def test_openai_build_missing_resume_authority_retains_prepared_refusal_then_fresh_grant(work, api):
    funded_registry(work)
    _, directory, _ = prepare_build(work)
    api.owner = directory
    execute_task(directory, allow_external=True, allow_api_spend=True, max_operations=2)
    refused = execute_task(directory, allow_external=True)
    assert len(api.calls) == 1
    event = refused['build']['events'][-1]
    assert event['phase'] == 'prepared' and event['funding']['api_authorized'] is False
    assert event['funding']['dispatch_outcome'] == 'not_started'
    completed = execute_task(directory, allow_external=True, allow_api_spend=True)
    assert completed['build']['status'] == 'completed', completed['build'].get('error')
    assert len(api.calls) == 3
    assert canonical(completed) == canonical(read_task(directory))


@pytest.mark.parametrize('phase', ['planning', 'build'])
def test_openai_work_readers_refuse_consistently_corrupted_configuration_evidence(work, api, phase):
    if phase == 'build' and os.name != 'posix':
        pytest.skip('POSIX build profile only')
    funded_registry(work)
    if phase == 'planning':
        make(work)
        directory = work[2]['directory']
    else:
        _, directory, _ = prepare_build(work)
    api.owner = directory
    completed = execute_task(directory, allow_external=True, allow_api_spend=True)
    assert completed[phase]['status'] == 'completed', completed[phase].get('error')

    def corrupt(value):
        if isinstance(value, dict):
            if value.get('profile') == 'participant-funding-v1':
                value['configuration_digest'] = '0' * 64
            for nested in value.values():
                corrupt(nested)
        elif isinstance(value, list):
            for nested in value:
                corrupt(nested)

    corrupt(completed)
    with RunStore(directory, existing=True).lease():
        RunStore(directory, existing=True).save(completed)
    count = len(api.calls)
    with pytest.raises(ValueError, match='[Ff]unding'):
        read_task(directory)
    assert len(api.calls) == count
