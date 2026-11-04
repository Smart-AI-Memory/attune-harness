"""Legacy native request bytes stay distinct from strict API owner binding."""
# qualify: platform

import hashlib
import json

import pytest

from attune_harness import review_participants


@pytest.mark.parametrize('adapter', ['claude', 'codex'])
def test_native_review_preserves_raw_objective_and_legacy_envelope(monkeypatch, tmp_path, adapter):
    captured = []

    class InertNative:
        identity = None

        def __init__(self, provider, **kwargs):
            assert provider == adapter

        def __call__(self, raw):
            captured.append(json.loads(raw)['attempt']['task']['objective'])
            return json.dumps({'version': 1, 'request_digest': hashlib.sha256(raw.encode()).hexdigest(),
                               'text': 'Offline legacy response'})

    monkeypatch.setattr(review_participants, 'NativeExchange', InertNative)
    turn = {'task_id': 'fixture', 'role': 'lead', 'turn_id': 'fixture-turn',
            'requirement_revision': 'fixture-revision', 'participant_id': 'peer'}
    # The original direct native boundary does not validate these outer fields.
    # Its action owner still validates normal workflow response correlation.
    raw = json.dumps({'schema_version': 7, 'request_digest': 'legacy-opaque',
                      'turn': turn, 'legacy_extension': 'Café'}, indent=3, ensure_ascii=False) + '\n'
    configuration = {'adapter': adapter, 'model': 'offline-native', 'timeout': 5, 'tools': []}
    assert review_participants.ReviewExchange(configuration, tmp_path)(raw) == 'Offline legacy response'
    assert captured == [raw]


@pytest.mark.parametrize('corruption', ['fields', 'version', 'digest'])
def test_api_model_attempt_keeps_strict_owner_envelope(corruption):
    turn = {'task_id': 'fixture', 'role': 'lead', 'turn_id': 'fixture-turn',
            'requirement_revision': 'fixture-revision', 'participant_id': 'peer'}
    request = {'schema_version': 1, 'request_digest': review_participants.digest(turn), 'turn': turn}
    if corruption == 'fields':
        request['legacy_extension'] = 'Refused for API'
    elif corruption == 'version':
        request['schema_version'] = 7
    else:
        request['request_digest'] = 'legacy-opaque'
    with pytest.raises(ValueError):
        review_participants.model_attempt({'adapter': 'openai'}, request, 'harness-review-v1')
