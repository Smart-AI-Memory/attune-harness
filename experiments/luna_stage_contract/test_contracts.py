"""Operational fixtures, including saved failure; no provider calls."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from contracts import TEXT, assess, select_message

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))


def wrap(payload, arm):
    text = json.dumps(payload)
    return json.dumps({'text': text}) if arm == 'text' else text


@pytest.mark.parametrize('arm', ['text', 'stage'])
def test_required_read_and_unavailable_scope(arm):
    assert assess(wrap({'actions': [{'tool': 'read', 'source_id': 'S2'}]}, arm), arm, CASES[0])['mechanical_case_pass']
    assert assess(wrap({'actions': []}, arm), arm, CASES[1])['mechanical_case_pass']
    assert not assess(wrap({'actions': []}, arm), arm, CASES[0])['mechanical_case_pass']
    assert not assess(wrap({'actions': [{'tool': 'read', 'source_id': 'S99'}]}, arm), arm, CASES[0])['mechanical_case_pass']


@pytest.mark.parametrize('arm', ['text', 'stage'])
def test_shape_does_not_establish_decision_correctness(arm):
    wrong = {'decision': 'update', 'memory': 'Use Anthropic exclusively.', 'source_ids': ['S2']}
    result = assess(wrap(wrong, arm), arm, CASES[3])
    assert result['shape_valid'] and not result['mechanical_case_pass']
    correct = {'decision': 'no_change', 'memory': '', 'source_ids': ['S2']}
    assert assess(wrap(correct, arm), arm, CASES[3])['mechanical_case_pass']


def test_preserving_an_exception_requires_prose_review_even_with_right_fields():
    value = {'decision': 'update', 'memory': 'Always upload everything to OpenAI.', 'source_ids': ['S2', 'S3']}
    result = assess(json.dumps(value), 'stage', CASES[2])
    assert result['mechanical_case_pass']
    assert result['prose_grade'] == 'required'


@pytest.mark.parametrize('payload', [
    {'actions': [], 'answer': 'Premature'},
    {'actions': [{'tool': 'write', 'source_id': 'S2'}]},
    {'actions': [{'tool': 'read', 'source_id': 'S2'}] * 4},
    {'actions': [{'tool': 'read'}]},
])
def test_malformed_actions_rejected(payload):
    with pytest.raises(ValidationError):
        assess(json.dumps(payload), 'stage', CASES[0])


def test_duplicate_json_fields_rejected():
    with pytest.raises(ValueError, match='Duplicate'):
        assess('{"actions": [], "actions": []}', 'stage', CASES[0])


def test_saved_luna_failure_passes_outer_schema_but_not_inspection():
    path = ROOT / '.pilot/voyage-answer-accuracy-2026-09-15/extension-live/2b782af543291bb141ee8645-inspect-2-native.json'
    saved = json.loads(path.read_text(encoding='utf-8'))
    envelope = {'text': saved['result']['text']}
    Draft202012Validator(TEXT).validate(envelope)
    with pytest.raises(ValueError):
        assess(json.dumps(envelope), 'text', CASES[0])
    with pytest.raises(ValidationError):
        assess(json.dumps(envelope), 'stage', CASES[0])


def events(messages, *, extra=None, usage=True):
    rows = [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': text}} for text in messages]
    if extra:
        rows.insert(0, {'type': 'item.completed', 'item': extra})
    rows.append({'type': 'turn.completed', 'usage': {'input_tokens': 8, 'output_tokens': 4} if usage else {}})
    return '\n'.join(json.dumps(row) for row in rows)


def test_duplicate_identical_payloads_count_without_ambiguity():
    raw = events(['{"actions": []}', '{"actions":[]}'])
    text, usage, warnings, count = select_message(raw)
    assert json.loads(text) == {'actions': []} and count == 2
    assert usage['output_tokens'] == 4 and warnings == []


@pytest.mark.parametrize('raw', [
    events(['{"actions": []}'], extra={'type': 'command_execution', 'command': 'echo bad'}),
    events(['{"actions": []}'], extra={'type': 'error', 'message': 'Provider capacity failure'}),
    events(['{"actions": []}', '{"actions": [{"tool":"read","source_id":"S2"}]}']),
    events(['{"actions": []}'], usage=False),
    events(['{"actions": []}']) + '\n' + json.dumps({'type': 'turn.started'}),
])
def test_native_boundary_stops_before_more_dispatch(raw):
    with pytest.raises(ValueError):
        select_message(raw)


@pytest.mark.parametrize('failure_kind', ['missing_usage', 'unexpected_tool', 'unknown_error'])
def test_controller_records_unknown_boundary_and_stops(tmp_path, monkeypatch, failure_kind):
    import run as runner
    from attune_harness.process import ProcessResult

    packet = {'order': [{'case_id': case['id'], 'arm': arm} for case in CASES for arm in ('text', 'stage')],
              'max_native_calls': 8}
    (tmp_path / 'protocol.json').write_text(json.dumps(packet), encoding='utf-8')
    monkeypatch.setattr(runner, 'DEST', tmp_path)
    monkeypatch.setattr(runner, 'protocol', lambda: packet)
    calls = []

    def fake_invoke(argv, prompt, **kwargs):
        calls.append(argv)
        extra = ({'type': 'error', 'message': 'Provider capacity failure'}
                 if failure_kind == 'unknown_error' else {'type': 'command_execution'})
        raw = (events(['{"text":"{}"}'], usage=False) if failure_kind == 'missing_usage'
               else events(['{"text":"{}"}'], extra=extra))
        return ProcessResult(argv, 0, raw, '')

    monkeypatch.setattr(runner, 'invoke', fake_invoke)
    with pytest.raises(ValueError):
        runner.run()
    ledger = json.loads((tmp_path / 'ledger.json').read_text(encoding='utf-8'))
    assert len(calls) == 1 and ledger['status'] == 'stopped'
    assert ledger['attempts'][0]['state'] == 'unresolved'
    with pytest.raises(FileExistsError):
        runner.run()
    assert len(calls) == 1


def test_controller_rejects_more_than_eight_calls_before_dispatch(tmp_path, monkeypatch):
    import run as runner

    packet = {'order': [{}] * 9, 'max_native_calls': 8}
    (tmp_path / 'protocol.json').write_text(json.dumps(packet), encoding='utf-8')
    monkeypatch.setattr(runner, 'DEST', tmp_path)
    monkeypatch.setattr(runner, 'protocol', lambda: packet)
    with pytest.raises(ValueError, match='eight-call'):
        runner.run()
    assert not (tmp_path / 'ledger.json').exists()
