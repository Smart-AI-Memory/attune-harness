"""Offline native proposal boundaries: retained evidence, isolation, no retries.

The process seam is injected; these tests do not qualify the SDK or a live model.
"""

import base64
from copy import deepcopy
import hashlib

import pytest

from attune_harness import memory_native as native
from attune_harness.features import FeatureUnavailable
from attune_harness.process import ProcessResult
from attune_harness.review_contract import canonical, parse_json


@pytest.fixture
def config():
    return {
        'schema_version': 1, 'transport': native.TRANSPORT,
        'sdk_version': native.SDK_VERSION, 'httpx2_version': native.HTTPX2_VERSION,
        'endpoint': native.ENDPOINT,
        'auth': {'kind': 'environment', 'name': 'ANTHROPIC_API_KEY'},
        'phase_timeout_seconds': 10, 'wall_timeout_seconds': 15,
        'response_byte_limit': 2048,
        'profiles': {'routine': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                                 'max_tokens': 512}},
    }


@pytest.fixture
def message():
    return {
        'type': 'message', 'role': 'assistant', 'model': 'claude-sonnet-4-6',
        'stop_reason': 'end_turn', 'id': 'msg_offline',
        'content': [{'type': 'text', 'text': canonical({'outcome': 'proposal'})}],
        'usage': {'input_tokens': 12, 'output_tokens': 5},
    }


def receipt_for(message):
    raw = canonical(message).encode('utf-8')
    return {
        'state': 'completed', 'http_status': 200, 'request_id': 'req_offline',
        'raw_base64': base64.b64encode(raw).decode('ascii'),
        'raw_sha256': hashlib.sha256(raw).hexdigest(), 'raw_bytes': len(raw),
        'truncated': False,
    }


@pytest.fixture
def isolated_native(monkeypatch):
    for name in native.DENIED_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'offline-test-key')
    monkeypatch.setenv('HTTPS_PROXY', 'http://must-not-inherit.invalid')
    monkeypatch.setenv('UNRELATED_SECRET', 'must-not-inherit')
    monkeypatch.setattr(native, 'runtime_identity', lambda: {'offline': True})
    # A missing process stub must fail instead of launching the provider helper.
    def refuse(*args, **kwargs):
        pytest.fail('Unexpected native helper launch')
    monkeypatch.setattr(native, 'invoke', refuse)


@pytest.mark.parametrize('field,value', [
    ('raw_base64', 'not-base64!'), ('raw_sha256', '0' * 64),
    ('raw_bytes', 0), ('raw_bytes', True), ('http_status', 201),
    ('http_status', True), ('truncated', True), ('state', 'unresolved'),
])
def test_changed_receipt_is_refused_with_original_evidence(message, field, value):
    receipt = receipt_for(message)
    receipt[field] = value
    before = deepcopy(receipt)
    with pytest.raises(native.NativeMemoryError) as raised:
        native.decode_provider(receipt, {'model': message['model']})
    assert raised.value.evidence == before
    assert receipt == before


@pytest.mark.parametrize('field,value', [
    ('model', 'unaccepted-model'), ('role', 'user'), ('type', 'error'),
    ('stop_reason', 'max_tokens'), ('stop_reason', 'tool_use'),
    ('content', []),
    ('content', [{'type': 'tool_use', 'name': 'write_file'}]),
    ('content', [{'type': 'text', 'text': '{}'}, {'type': 'text', 'text': '{}'}]),
    ('content', [{'type': 'text', 'text': 'not json'}]),
    ('usage', {'input_tokens': -1, 'output_tokens': 5}),
    ('usage', {'input_tokens': 12, 'output_tokens': True}),
    ('usage', None),
])
def test_incomplete_or_mismatched_provider_message_is_not_a_proposal(message, field, value):
    message[field] = value
    receipt = receipt_for(message)
    with pytest.raises(native.NativeMemoryError) as raised:
        native.decode_provider(receipt, {'model': 'claude-sonnet-4-6'})
    assert raised.value.evidence == receipt


def run_stubbed(monkeypatch, config, stdout, returncode=0, failure=None):
    calls = []
    def invoke(argv, packet, **kwargs):
        calls.append((argv, parse_json(packet), kwargs))
        return ProcessResult(argv, returncode, stdout, '', failure)
    monkeypatch.setattr(native, 'invoke', invoke)
    actor = native.NativeParticipant(config)
    return actor, calls


def test_completed_reply_is_replayable_and_child_gets_only_explicit_environment(
    monkeypatch, config, message, isolated_native,
):
    receipt = receipt_for(message)
    actor, calls = run_stubbed(monkeypatch, config, canonical(receipt))
    prompt, schema = {'source': 'untrusted evidence'}, {'type': 'object'}
    reply = actor('worker', 'routine', prompt, schema)
    assert reply['value'] == {'outcome': 'proposal'}
    assert len(calls) == 1
    argv, packet, options = calls[0]
    assert argv[1:4] == ('-I', '-B', '-c')
    assert options['environment'] == {
        'ANTHROPIC_API_KEY': 'offline-test-key', 'LANG': 'C.UTF-8', 'LC_ALL': 'C',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
    }
    assert options['timeout'] == 15
    assert options['max_output_bytes'] == 4 * ((2048 + 2) // 3) + 262144
    assert options['capture_interrupt'] is True
    assert 'offline-test-key' not in canonical(packet)
    request = parse_json(packet['body']['messages'][0]['content'])
    assert request['prompt'] == prompt
    assert request['output_schema'] == schema
    assert 'tools' not in packet['body']
    assert native.validate_evidence(reply['evidence'], packet['body']) == reply['value']


@pytest.mark.parametrize('failure,returncode', [
    ('timeout_effects_unknown', None), ('output_limit', -9), ('interrupted_effects_unknown', -9),
    ('launch_failed', None), (None, 1),
])
def test_uncertain_helper_outcome_retains_diagnostics_and_does_not_retry(
    monkeypatch, config, isolated_native, failure, returncode,
):
    actor, calls = run_stubbed(monkeypatch, config, 'partial reply', returncode, failure)
    with pytest.raises(native.NativeMemoryError, match='helper outcome is unresolved') as raised:
        actor('worker', 'routine', {}, {})
    assert len(calls) == 1
    assert raised.value.evidence['stdout'] == 'partial reply'
    assert raised.value.evidence['returncode'] == returncode
    assert raised.value.evidence['failure'] == failure
    assert 'provider' not in raised.value.evidence


@pytest.mark.parametrize('stdout', ['not json', '{"state":"unresolved"}', '{}'])
def test_bad_helper_reply_retains_outer_evidence_without_retry(
    monkeypatch, config, isolated_native, stdout,
):
    actor, calls = run_stubbed(monkeypatch, config, stdout)
    with pytest.raises(native.NativeMemoryError) as raised:
        actor('worker', 'routine', {}, {})
    assert len(calls) == 1
    assert raised.value.evidence['stdout'] == stdout


@pytest.mark.skipif(native.os.name != 'posix', reason='Native preflight is POSIX-only')
@pytest.mark.parametrize('name', native.DENIED_ENVIRONMENT)
def test_ambient_provider_override_is_refused_before_dispatch(
    monkeypatch, config, isolated_native, name,
):
    monkeypatch.setenv(name, 'override')
    with pytest.raises(FeatureUnavailable, match='ambient provider/header overrides'):
        native.NativeParticipant(config).preflight(
            {'access': {'profiles': ['routine']}},
            {'routine_profile': 'routine', 'stronger_profile': 'routine'},
        )


@pytest.mark.parametrize('change', ['stdout', 'identity', 'request', 'stderr', 'returncode'])
def test_saved_completion_cannot_change_its_projection(
    monkeypatch, config, message, isolated_native, change,
):
    actor, calls = run_stubbed(monkeypatch, config, canonical(receipt_for(message)))
    evidence = actor('worker', 'routine', {}, {})['evidence']
    body = calls[0][1]['body']
    if change == 'stdout':
        evidence['stdout'] = '{}'
    elif change == 'identity':
        evidence['identity']['model'] = 'different-model'
    elif change == 'request':
        body['max_tokens'] += 1
    elif change == 'stderr':
        evidence['stderr'] = 'unexpected diagnostic'
    else:
        evidence['returncode'] = 1
    with pytest.raises(ValueError):
        native.validate_evidence(evidence, body)
