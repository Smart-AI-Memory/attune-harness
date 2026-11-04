"""Owner-bound API journeys use synthetic credentials and an inert transport."""
# qualify: platform

import copy
import importlib
import json
import os
from pathlib import Path
import tempfile
from threading import Barrier

import pytest

from attune_harness import consultation
from attune_harness.cli import main
from attune_harness.consultation_preflight import preflight
from attune_harness.participant_funding import FundingRefused, _Admission
from attune_harness.process import ProcessResult
from attune_harness.review_contract import canonical, digest
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import PersistenceError, RunStore, read_record
from attune_harness.task_contract import accept_task, read_task
from test_review import case, change_config
from test_task_contract import draft, response


KEY_NAME = 'HARNESS_TEST_OPENAI_FUNDING_KEY'
KEY = 'synthetic_test_key_0123456789abcdefghijk'
MODEL = 'fixture-explicit-model-one'


@pytest.fixture
def tmp_path(tmp_path):
    """Keep Windows funding fixtures outside pytest's crowded suite directory."""
    if os.name == 'nt':
        return Path(tempfile.mkdtemp(prefix='funding-', dir=tmp_path.parent.parent)).resolve()
    return tmp_path


def seat(model=MODEL, credential=KEY_NAME):
    return {'adapter': 'openai', 'identity': {'provider': 'openai', 'model': model},
            'timeout': 10, 'funding': {'mode': 'api', 'credential_env': credential}}


def registry_participant(*, evidence=False):
    return {'adapter': 'openai', 'model': MODEL, 'timeout': 10,
            'tools': ['retrieve', 'verify'] if evidence else [],
            'max_turns': 3 if evidence else 1, 'max_tool_calls': 2 if evidence else 0,
            'funding': {'mode': 'api', 'credential_env': KEY_NAME},
            **({'review_mode': 'evidence'} if evidence else {})}


def configuration(*, rounds=1, second=False):
    return {'schema_version': 1, 'question': 'Inspect the frozen source and preserve uncertainty',
            'author': {'provider': 'codex', 'model': 'fixture-author-model'},
            'participants': {'reviewer': seat(), **(
                {'critic': seat('fixture-explicit-model-two', 'HARNESS_TEST_OPENAI_OTHER_KEY')}
                if second else {})}, 'rounds': rounds}


def prepare(tmp_path, *, rounds=1, second=False):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'x.py').write_text('x = 1\n', encoding='utf-8')
    directory = tmp_path / 'run'
    record = consultation.prepare('roundtable' if second else 'source-review', root, ['x.py'],
                                  configuration(rounds=rounds, second=second), directory)
    return directory, record


def provider_response(model, text, identifier='resp_fixture'):
    """Responses API fields consumed by the transport, with no billing claim."""
    return {'id': identifier, 'object': 'response', 'status': 'completed', 'model': model,
            'error': None, 'incomplete_details': None,
            'output': [{'id': 'msg_fixture', 'type': 'message', 'role': 'assistant',
                        'status': 'completed', 'content': [
                            {'type': 'output_text', 'text': canonical({'text': text}), 'annotations': []}]}],
            'usage': {'input_tokens': 13, 'output_tokens': 7, 'total_tokens': 20,
                      'input_tokens_details': {'cached_tokens': 3},
                      'output_tokens_details': {'reasoning_tokens': 2},
                      'billed_cost_usd': 999, 'remaining_balance': 999}}


class InertAPI:
    def __init__(self):
        self.calls = []
        self.transform = lambda value: value
        self.before = lambda **kwargs: None
        self.stderr = ''
        self.error = None
        self.stdout = None
        self.encode = canonical

    def __call__(self, argv, raw, **kwargs):
        packet = json.loads(raw)
        body = packet['body']
        attempt = json.loads(body['input'].split('\n', 1)[1])['attempt']
        objective = json.loads(attempt['task']['objective'])
        assert body['store'] is False and body['tools'] == []
        self.calls.append({'body': copy.deepcopy(body), 'attempt': attempt,
                           'environment': dict(kwargs['environment'])})
        self.before(**kwargs)
        if self.error:
            raise self.error
        if 'snapshot' in objective:
            text = canonical({'verdict': 'uncertain', 'summary': 'Synthetic source review; no model quality claim.',
                              'evidence': [{'path': 'x.py', 'line': 1, 'detail': 'Frozen assignment is visible.'}]})
        elif 'request_digest' in objective:
            text = canonical({'schema_version': 1, 'request_digest': objective['request_digest'],
                              'action': {'kind': 'final', 'text': 'Synthetic assessment preserves uncertainty.'}})
        else:
            text = ('The frozen reference supports only the stated fixture claim. '
                    'This synthetic review preserves uncertainty and does not certify arbitrary policy prose.')
        value = self.transform(provider_response(body['model'], text))
        return ProcessResult(tuple(argv), 0, self.stdout if self.stdout is not None else self.encode(value),
                             self.stderr)


@pytest.fixture
def api(monkeypatch):
    exchange = importlib.import_module('attune_harness.openai_exchange')
    monkeypatch.setenv(KEY_NAME, KEY)
    monkeypatch.setenv('HARNESS_TEST_OPENAI_OTHER_KEY', 'other_synthetic_key_9876543210abcdefghijk')
    monkeypatch.setenv('HARNESS_TEST_UNRELATED_SECRET', 'unrelated_synthetic_value')
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://synthetic.invalid')
    monkeypatch.setenv('HTTP_PROXY', 'https://synthetic-proxy.invalid')
    transport = InertAPI()
    monkeypatch.setattr(exchange, 'invoke', transport)

    def forbidden(*args, **kwargs):
        pytest.fail('A test attempted a native, provider, or status process')

    for module, name in (('attune_harness.consultation', 'invoke'),
                         ('attune_harness.consultation', 'NativeExchange'),
                         ('attune_harness.review_participants', 'invoke'),
                         ('attune_harness.review_participants', 'NativeExchange'),
                         ('attune_harness.consultation_preflight', 'invoke')):
        monkeypatch.setattr(importlib.import_module(module), name, forbidden)
    return transport


def assert_usage(identity):
    usage = identity['usage']
    assert usage['state'] == 'reported'
    assert (usage['input_tokens'], usage['output_tokens'], usage['cached_input_tokens']) == (13, 7, 3)
    assert all(usage[name] is None for name in ('cache_creation_tokens', 'provider_reported_cost_usd',
                                              'billed_cost_usd', 'remaining_balance'))


def test_consultation_check_prepare_run_status_is_owned_and_inspection_is_inert(tmp_path, api, capsys):
    checked = preflight(configuration())['reviewer']
    assert checked['state'] == 'unknown'
    assert checked['funding']['state'] == 'matched'
    assert checked['binary'] is None and checked['version'] is None
    directory, prepared = prepare(tmp_path)
    assert api.calls == [] and prepared['events'] == []

    def persisted_before_dispatch(**kwargs):
        saved = consultation.load(directory)
        event = saved['events'][0]
        assert event['phase'] == 'dispatching'
        assert event['funding']['state'] == 'matched'
        assert event['funding']['api_authorized'] is True

    api.before = persisted_before_dispatch
    completed = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert completed['status'] == 'completed'
    assert len(api.calls) == 1
    assert canonical(completed) == canonical(consultation.load(directory))
    event = completed['events'][0]
    assert event['funding']['dispatch_outcome'] == 'completed'
    assert event['funding'] == event['result']['identity']['funding']
    assert_usage(event['result']['identity'])
    original = (directory / 'record.json').read_bytes()
    assert main(['source-review', 'status', str(directory)]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown['events'][0]['funding']['state'] == 'matched'
    assert len(api.calls) == 1 and (directory / 'record.json').read_bytes() == original
    assert KEY not in original.decode('utf-8')


def test_missing_api_authority_retains_prepared_refusal_and_can_be_freshly_authorized(tmp_path, api):
    directory, prepared = prepare(tmp_path)
    with pytest.raises(FundingRefused, match='api_authority_required'):
        consultation.run(directory, prepared['contract_digest'], allow_external=True)
    assert api.calls == []
    refused = consultation.load(directory)['events'][0]
    assert refused['phase'] == 'prepared'
    assert refused['funding']['api_authorized'] is False
    assert refused['funding']['dispatch_outcome'] == 'not_started'
    done = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert done['status'] == 'completed' and len(api.calls) == 1
    assert done['events'][0]['funding_history'][0]['api_authorized'] is False


def test_roundtable_resume_requires_fresh_authority_for_remaining_calls(tmp_path, api):
    directory, prepared = prepare(tmp_path, second=True, rounds=2)
    first = consultation.run(directory, prepared['contract_digest'], allow_external=True,
                             allow_api_spend=True, max_operations=2)
    assert first['status'] == 'paused' and len(api.calls) == 2
    with pytest.raises(FundingRefused, match='api_authority_required'):
        consultation.run(directory, prepared['contract_digest'], allow_external=True)
    assert len(api.calls) == 2
    refused = consultation.load(directory)['events'][-1]
    assert refused['phase'] == 'prepared' and refused['funding']['api_authorized'] is False
    done = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert done['status'] == 'completed' and len(api.calls) == 4


def test_roundtable_admits_every_sibling_before_any_dispatch(tmp_path, api, monkeypatch):
    monkeypatch.delenv('HARNESS_TEST_OPENAI_OTHER_KEY')
    directory, prepared = prepare(tmp_path, second=True)
    with pytest.raises(FundingRefused, match='missing_credential'):
        consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert api.calls == []
    saved = consultation.load(directory)
    assert len(saved['events']) == 2
    assert all(event['phase'] == 'prepared' for event in saved['events'])
    assert all(event['funding']['dispatch_outcome'] == 'not_started' for event in saved['events'])
    monkeypatch.setenv('HARNESS_TEST_OPENAI_OTHER_KEY', 'other_synthetic_key_9876543210abcdefghijk')
    done = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert done['status'] == 'completed' and len(api.calls) == 2


@pytest.mark.parametrize('credential', [None, '', 'short', 'synthetic credential with spaces'])
def test_missing_or_invalid_selected_key_refuses_before_runner(tmp_path, api, monkeypatch, credential):
    if credential is None:
        monkeypatch.delenv(KEY_NAME)
    else:
        monkeypatch.setenv(KEY_NAME, credential)
    assert preflight(configuration())['reviewer']['funding']['state'] == 'missing_credential'
    directory, prepared = prepare(tmp_path)
    with pytest.raises(FundingRefused, match='missing_credential'):
        consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert api.calls == []
    event = consultation.load(directory)['events'][0]
    assert event['phase'] == 'prepared'
    assert event['funding']['state'] == 'missing_credential'
    assert event['funding']['dispatch_outcome'] == 'not_started'


@pytest.mark.parametrize('point', ['admitted_prepared', 'dispatch_boundary'])
def test_persistence_failure_prevents_dispatch_and_saved_authority_is_not_reused(tmp_path, api, monkeypatch, point):
    directory, prepared = prepare(tmp_path)
    original = RunStore.save

    def fail(store, record):
        if any(event.get('funding', {}).get('state') == 'matched' and (
                point == 'admitted_prepared' or event['phase'] == 'dispatching')
                for event in record['events']):
            raise PersistenceError('Synthetic admission persistence failure')
        return original(store, record)

    monkeypatch.setattr(RunStore, 'save', fail)
    with pytest.raises(PersistenceError, match='Synthetic admission persistence failure'):
        consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert api.calls == []
    monkeypatch.setattr(RunStore, 'save', original)
    assert consultation.load(directory)['events'][0]['phase'] == 'prepared'
    with pytest.raises(FundingRefused, match='api_authority_required'):
        consultation.run(directory, prepared['contract_digest'], allow_external=True)
    assert api.calls == []


@pytest.mark.parametrize('echo', [
    'stdout', 'stderr', 'exception', 'native_exception', 'answer',
    'escaped_answer', 'nested_encoded_answer', 'escaped_id',
])
def test_provider_key_echo_never_reaches_saved_records_or_status(tmp_path, api, capsys, echo):
    if echo == 'stdout':
        api.stdout = KEY
    elif echo == 'stderr':
        api.stderr = KEY
    elif echo == 'exception':
        api.error = RuntimeError('Synthetic diagnostic ' + KEY)
    elif echo == 'native_exception':
        from attune_harness.native import NativeError
        api.error = NativeError('Synthetic diagnostic ' + KEY, failure=KEY,
                                refusal={'diagnostic': KEY})
    else:
        def echo_answer(value):
            value['output'][0]['content'][0]['text'] = canonical({'text': canonical(
                {'verdict': 'uncertain', 'summary': KEY, 'evidence': []})})
            return value
        api.transform = echo_answer
        if echo in ('escaped_answer', 'escaped_id'):
            escaped_key = ''.join('\\u%04x' % ord(character) for character in KEY)
            api.encode = lambda value: canonical(value).replace(KEY, escaped_key)
        if echo == 'escaped_id':
            def echo_id(value):
                value['id'] = KEY
                return value
            api.transform = echo_id
        elif echo == 'nested_encoded_answer':
            def nested_echo(value):
                value = echo_answer(value)
                escaped_key = ''.join('\\u%04x' % ord(character) for character in KEY)
                value['output'][0]['content'][0]['text'] = value['output'][0]['content'][0]['text'].replace(
                    KEY, escaped_key)
                return value
            api.transform = nested_echo
    directory, prepared = prepare(tmp_path)
    result = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    if echo == 'escaped_id':
        assert result['status'] in ('completed', 'failed')
    else:
        assert result['status'] == ('failed' if echo in ('stdout', 'exception', 'native_exception') else 'completed')
    assert len(api.calls) == 1
    assert KEY not in canonical(result)
    assert KEY not in (directory / 'record.json').read_text(encoding='utf-8')
    main(['source-review', 'status', str(directory)])
    assert KEY not in capsys.readouterr().out


@pytest.mark.parametrize('corruption', [
    'different_model', 'missing_model', 'null_model', 'nonstring_model',
    'incomplete', 'wrong_content', 'wrong_role', 'missing_id',
])
def test_usage_does_not_make_invalid_provider_response_acceptable(tmp_path, api, corruption):
    def corrupt(value):
        if corruption == 'different_model':
            value['model'] = 'fixture-unselected-model'
        elif corruption == 'missing_model':
            del value['model']
        elif corruption == 'null_model':
            value['model'] = None
        elif corruption == 'nonstring_model':
            value['model'] = [MODEL]
        elif corruption == 'incomplete':
            value['status'] = 'incomplete'
        elif corruption == 'wrong_content':
            value['output'][0]['content'][0]['type'] = 'refusal'
        elif corruption == 'wrong_role':
            value['output'][0]['role'] = 'user'
        else:
            del value['id']
        return value
    api.transform = corrupt
    directory, prepared = prepare(tmp_path)
    failed = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert failed['status'] == 'failed' and len(api.calls) == 1
    event = failed['events'][0]
    assert event['funding']['dispatch_outcome'] == 'unknown'
    assert event['result']['answer'] is None
    assert event['result']['identity']['usage'] is None
    with pytest.raises(ValueError, match='Terminal'):
        consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert len(api.calls) == 1


@pytest.mark.parametrize('raw_usage,reason', [(None, 'missing'), ({'input_tokens': 13}, 'partial'),
                                            ({'input_tokens': True, 'output_tokens': 7}, 'invalid')])
def test_valid_output_with_unknown_usage_never_invents_counts_or_cost(tmp_path, api, raw_usage, reason):
    def usage(value):
        value['usage'] = raw_usage
        return value
    api.transform = usage
    directory, prepared = prepare(tmp_path)
    done = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert done['status'] == 'completed' and len(api.calls) == 1
    evidence = done['events'][0]['result']['identity']['usage']
    assert evidence['state'] == 'unknown' and evidence['reason'] == reason
    for name in ('input_tokens', 'output_tokens', 'cached_input_tokens', 'cache_creation_tokens',
                 'provider_reported_cost_usd', 'billed_cost_usd', 'remaining_balance'):
        assert evidence[name] is None


def test_concurrent_seats_receive_independent_selected_keys_and_parent_is_unchanged(tmp_path, api):
    barrier = Barrier(2)
    api.before = lambda **kwargs: barrier.wait(timeout=5)
    directory, prepared = prepare(tmp_path, second=True)
    completed = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
    assert completed['status'] == 'completed' and len(api.calls) == 2
    keyed = {call['body']['model']: call['environment'] for call in api.calls}
    assert keyed[MODEL]['OPENAI_API_KEY'] == KEY
    assert keyed['fixture-explicit-model-two']['OPENAI_API_KEY'] == 'other_synthetic_key_9876543210abcdefghijk'
    for environment in keyed.values():
        assert not ({KEY_NAME, 'HARNESS_TEST_OPENAI_OTHER_KEY', 'HARNESS_TEST_UNRELATED_SECRET',
                     'OPENAI_BASE_URL', 'HTTP_PROXY'} & environment.keys())
        assert set(environment) <= {'OPENAI_API_KEY', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP'}
    assert os.environ[KEY_NAME] == KEY
    assert os.environ['HARNESS_TEST_OPENAI_OTHER_KEY'] == 'other_synthetic_key_9876543210abcdefghijk'
    assert os.environ['OPENAI_BASE_URL'] == 'https://synthetic.invalid'
    assert os.environ['HTTP_PROXY'] == 'https://synthetic-proxy.invalid'


def test_direct_exchanges_without_persisted_admission_refuse(tmp_path, api):
    from attune_harness.openai_exchange import OpenAIExchange

    for admission in (None, _Admission({'OPENAI_API_KEY': KEY}, {})):
        with pytest.raises(ValueError, match='persisted admission'):
            OpenAIExchange(model=MODEL, cwd=tmp_path, admission=admission)
    turn = {'task_id': 'fixture-task', 'turn_id': 'fixture-turn', 'participant_id': 'alpha',
            'attempt_id': 'fixture-assignment', 'requirement_revision': 'a' * 64,
            'role': 'lead', 'tools': []}
    exchange = ReviewExchange(registry_participant(), tmp_path)
    with pytest.raises(ValueError, match='persisted admission'):
        exchange(canonical({'schema_version': 1, 'request_digest': digest(turn), 'turn': turn}))
    assert api.calls == []


def test_consumed_owner_admission_cannot_dispatch_again(tmp_path, api):
    from attune_harness.openai_exchange import OpenAIExchange

    directory, prepared = prepare(tmp_path)
    admissions = []

    def dispatch(config, turn, cwd, cancel, *, admission):
        admissions.append(admission)
        return consultation.dispatch(config, turn, cwd, cancel, admission=admission)

    done = consultation.run(directory, prepared['contract_digest'], allow_external=True,
                            allow_api_spend=True, dispatcher=dispatch)
    assert done['status'] == 'completed'
    assert admissions[0].used is True and admissions[0].environment == {}
    exchange = OpenAIExchange(model=MODEL, cwd=directory, admission=admissions[0])
    with pytest.raises(ValueError, match='already consumed'):
        exchange(canonical({'version': 1}))
    assert len(api.calls) == 1


def test_mutating_a_funded_exchange_cannot_select_a_legacy_transport(tmp_path, api):
    config = registry_participant()
    exchange = ReviewExchange(config, tmp_path)
    config['adapter'] = 'codex'
    del config['funding']
    with pytest.raises(ValueError, match='Funding configuration changed'):
        exchange('{}')
    assert api.calls == []


@pytest.mark.parametrize('evidence', [False, True])
def test_registry_review_success_binds_api_evidence_and_host_steps_do_not_consume_it(case, api, evidence):
    review = importlib.import_module('attune_harness.review')
    change_config(case, lambda value: value['participants'].update(alpha=registry_participant(evidence=evidence)))

    def durable(**kwargs):
        saved = read_record(case[2])
        events = [event for event in saved['events'] if event.get('funding')]
        assert len(events) == 1 and events[0]['phase'] == 'dispatching'

    api.before = durable
    result = review.review(*case, allow_external=True, allow_api_spend=True)
    assert result['status'] == 'completed', result.get('error')
    assert len(api.calls) == 1
    funded = [event for event in result['events'] if 'funding' in event]
    assert len(funded) == 1
    assert funded[0]['result']['identity']['funding'] == funded[0]['funding']
    assert_usage(funded[0]['result']['identity'])
    if evidence:
        host_steps = [event for event in result['events'] if
                      (event.get('result') or {}).get('identity', {}).get('adapter') == 'host-evidence']
        assert len(host_steps) == 2 and all('funding' not in event for event in host_steps)
    assert KEY not in canonical(result)


def test_assessment_resume_requires_fresh_api_authority_and_does_not_save_a_grant(case, api):
    from attune_harness.task_policies import execute_task

    change_config(case, lambda value: value['participants'].update(alpha=registry_participant()))
    draft(case)
    accepted = response(case[2])
    accepted['permissions']['external'] = True
    accept_task(case[2], accepted)
    paused = execute_task(case[2], allow_api_spend=True, max_operations=2)
    assert paused['status'] == 'paused' and api.calls == []
    refused = execute_task(case[2])
    assert refused['status'] == 'paused' and api.calls == []
    assert refused['execution']['events'][-1]['phase'] == 'prepared'
    event = refused['execution']['events'][-1]
    assert event['phase'] == 'prepared' and event['funding']['api_authorized'] is False
    assert refused['acceptance']['permissions'] == {'external': True, 'provider': False}
    done = execute_task(case[2], allow_api_spend=True)
    assert done['status'] == 'completed' and len(api.calls) == 1
    assert done['acceptance']['permissions'] == {'external': True, 'provider': False}
    assert_usage(done['execution']['events'][-2]['result']['identity'])
    assert KEY not in canonical(read_task(case[2]))


@pytest.mark.parametrize('owner', ['consultation', 'assessment'])
@pytest.mark.parametrize('binding', ['configuration_digest', 'participant_id', 'attempt_id', 'identity', 'missing'])
def test_saved_funding_must_match_accepted_owner_bindings(tmp_path, case, api, owner, binding):
    if owner == 'consultation':
        directory, prepared = prepare(tmp_path)
        completed = consultation.run(directory, prepared['contract_digest'], allow_external=True, allow_api_spend=True)
        events = completed['events']
        reader = consultation.load
    else:
        from attune_harness.task_policies import execute_task
        change_config(case, lambda value: value['participants'].update(alpha=registry_participant()))
        draft(case)
        accepted = response(case[2])
        accepted['permissions']['external'] = True
        accept_task(case[2], accepted)
        directory = case[2]
        completed = execute_task(directory, allow_api_spend=True)
        assert completed['status'] == 'completed', completed.get('error')
        events = completed['execution']['events']
        reader = read_task
    event = next(event for event in events if 'funding' in event)
    if binding == 'identity':
        event['result']['identity']['funding']['configuration_digest'] = '0' * 64
    elif binding == 'missing':
        del event['funding']
    else:
        selected_digest = event['funding']['request_digest']
        replacement = '0' * 64 if binding == 'configuration_digest' else 'unaccepted-fixture-binding'

        def replace_consistently(value):
            if isinstance(value, dict):
                if (value.get('profile') == 'participant-funding-v1'
                        and value.get('request_digest') == selected_digest):
                    value[binding] = replacement
                for nested in value.values():
                    replace_consistently(nested)
            elif isinstance(value, list):
                for nested in value:
                    replace_consistently(nested)

        replace_consistently(completed)
    store = RunStore(directory, existing=True)
    with store.lease():
        store.save(completed)
    before = len(api.calls)
    with pytest.raises(ValueError, match='[Ff]unding|API operation|admission'):
        reader(directory)
    assert len(api.calls) == before
