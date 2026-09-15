import copy
import json

import pytest

from attune_harness import Task
from attune_harness.adapters import Attempt, JsonParticipant
from attune_harness.ollama import LocalJsonExchange, LocalModel, LocalModelError, ModelPin, NoRedirect, local_request


@pytest.fixture
def server():
    pin = ModelPin('local:8b', 'a' * 64, '0.31.1')
    state = {'version': {'version': '0.31.1'}, 'tags': {'models': [{'name': 'local:8b', 'digest': 'a' * 64,
        'size': 42, 'details': {'format': 'gguf'}, 'capabilities': ['completion']}]},
        'generate': {'model': 'local:8b', 'done': True, 'done_reason': 'stop', 'response': '{"answer":42}',
          'prompt_eval_count': 20, 'eval_count': 6, 'total_duration': 100, 'load_duration': 0,
          'prompt_eval_duration': 20, 'eval_duration': 80}}
    calls = []
    def request(endpoint, payload=None, **kwargs):
        calls.append((endpoint, copy.deepcopy(payload)))
        return copy.deepcopy(state[endpoint])
    model = LocalModel(pin, request=request)
    return model, state, calls


def generate(model, **kwargs):
    arguments = {'system': 'Compute.', 'schema': {'type': 'object'}, 'seed': 1,
                 'options': {'temperature': 0.2, 'num_ctx': 4096, 'num_predict': 192}}
    arguments.update(kwargs)
    return model.generate('17 + 25', **arguments)


def test_pinned_local_call_reports_usage_and_checks_identity_twice(server):
    model, _, calls = server
    result = generate(model)
    assert result['response'] == '{"answer":42}' and result['local_identity']['digest'] == 'a' * 64
    assert [c[0] for c in calls] == ['version', 'tags', 'generate', 'version', 'tags']
    assert calls[2][1]['stream'] is False and calls[2][1]['options']['seed'] == 1


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'digest', 'remote-host', 'remote-model', 'zero-size', 'format', 'embedding', 'unknown-capability', 'version'])
def test_unqualified_model_never_generates(server, fault):
    model, state, calls = server
    entry = state['tags']['models'][0]
    if fault == 'missing': state['tags']['models'] = []
    elif fault == 'duplicate': state['tags']['models'].append(copy.deepcopy(entry))
    elif fault == 'digest': entry['digest'] = 'b' * 64
    elif fault == 'remote-host': entry['remote_host'] = 'https://remote.example'
    elif fault == 'remote-model': entry['remote_model'] = 'hosted'
    elif fault == 'zero-size': entry['size'] = 0
    elif fault == 'format': entry['details']['format'] = 'remote'
    elif fault == 'embedding': entry['capabilities'] = ['embedding']
    elif fault == 'unknown-capability': entry.pop('capabilities')
    else: state['version']['version'] = 'other'
    with pytest.raises(LocalModelError): generate(model)
    assert not any(c[0] == 'generate' for c in calls)


@pytest.mark.parametrize('field,value', [('done', False), ('done', 1), ('done_reason', 'length'), ('model', 'other'),
    ('response', ''), ('prompt_eval_count', -1), ('eval_count', False), ('total_duration', None)])
def test_incomplete_or_invalid_generation_keeps_raw_evidence_and_never_retries(server, field, value):
    model, state, calls = server
    state['generate'][field] = value
    with pytest.raises(LocalModelError): generate(model)
    assert sum(c[0] == 'generate' for c in calls) == 1
    assert model.last_response[field] == value


def test_metadata_drift_after_generation_refuses_success(server):
    model, state, _ = server
    original = model.request
    def request(endpoint, payload=None, **kwargs):
        result = original(endpoint, payload, **kwargs)
        if endpoint == 'generate': state['tags']['models'][0]['digest'] = 'b' * 64
        return result
    model.request = request
    with pytest.raises(LocalModelError): generate(model)
    assert model.last_response['response'] == '{"answer":42}'


@pytest.mark.parametrize('change', [{'seed': True}, {'seed': -1}, {'options': {'num_ctx': True, 'num_predict': 192}},
    {'options': {'num_ctx': 4096, 'num_predict': 192, 'temperature': float('nan')}},
    {'options': {'num_ctx': 4096, 'num_predict': 192, 'remote': 1}}, {'schema': 'json'}])
def test_invalid_request_is_rejected_before_model_access(server, change):
    model, _, calls = server
    with pytest.raises(ValueError): generate(model, **change)
    assert calls == []


def test_json_exchange_works_through_existing_attempt_contract(server):
    model, _, _ = server
    exchange = LocalJsonExchange(model, system='Compute', schema={'type': 'object'}, seed=1,
                                 options={'num_ctx': 4096, 'num_predict': 192})
    task = Task('test', '17 + 25', ('Answer the arithmetic task.',))
    participant = JsonParticipant(Attempt(task, 'one', 'revision', 'local', 'lead', 'local-v1'), exchange)
    assert json.loads(participant.run(task).text) == {'answer': 42}
    with pytest.raises(RuntimeError): participant.run(task)


def test_redirect_and_unknown_endpoints_are_never_followed():
    with pytest.raises(LocalModelError): NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere')
    with pytest.raises(ValueError): local_request('pull', {'model': 'anything'})


def test_large_prompt_is_refused_before_any_model_request(server):
    model, _, calls = server
    with pytest.raises(ValueError):
        model.generate('x' * 4096, system='', schema={'type': 'object'}, seed=1, options={'num_ctx': 4096, 'num_predict': 192})
    assert calls == []


@pytest.mark.parametrize('body', [b'Failed to parse grammar', b'oversized-body:' + b'x' * 5000])
def test_http_error_retains_bounded_diagnostic_without_retry(monkeypatch, body):
    import io
    import urllib.error
    from types import SimpleNamespace
    calls = []
    def fail(*args, **kwargs):
        calls.append(args)
        raise urllib.error.HTTPError('http://127.0.0.1:11434/api/generate', 400, 'Bad Request', {}, io.BytesIO(body))
    monkeypatch.setattr('urllib.request.build_opener', lambda *args: SimpleNamespace(open=fail))
    with pytest.raises(LocalModelError) as captured:
        local_request('generate', {})
    message = str(captured.value)
    assert 'HTTP 400' in message and body[:20].decode() in message
    assert len(message) < 4300
    assert ('[truncated]' in message) == (len(body) > 4096)
    assert len(calls) == 1
