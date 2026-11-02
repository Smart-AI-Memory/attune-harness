"""Direct native review objects preserve host validation and legacy replay."""
# qualify: platform

import copy
import json
from pathlib import Path

import pytest

from attune_harness import consultation as c
from attune_harness.native import NativeExchange, TEXT_SCHEMA
from attune_harness.process import ProcessResult
from attune_harness.review_contract import digest
from attune_harness.review_store import RunStore


def configuration(provider='codex', timeout=600, *, two=False):
    seat = {'adapter': provider, 'identity': {'provider': provider, 'model': 'fixture-model'},
            'timeout': timeout}
    seats = {'reviewer': seat}
    if two:
        seats['critic'] = {**seat, 'identity': {'provider': provider, 'model': 'fixture-critic'}}
    return {'schema_version': 1, 'question': 'Inspect selected evidence',
            'author': {'provider': 'host', 'model': 'author'}, 'participants': seats, 'rounds': 1}


def prepare(tmp_path, provider='codex', *, two=False, legacy=False):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'x.py').write_text('x = 1\n', encoding='utf-8')
    directory = tmp_path / 'run'
    cfg = configuration(provider, timeout=300 if legacy else 600, two=two)
    record = c.prepare('roundtable' if two else 'source-review', source, ['x.py'], cfg, directory)
    if legacy:
        # A pre-change preparation has no response marker; its accepted turn
        # shape must remain byte-identical through a later pause and resume.
        record['contract'].pop('native_response_profile')
        record['contract_digest'] = digest(record['contract'])
        store = RunStore(directory, existing=True)
        with store.lease():
            store.save(record)
    return directory, record


def payload():
    return {'verdict': 'request_changes', 'summary': 'Quote " and path C:\\work\nUnicode: café',
            'evidence': [{'path': 'x.py', 'line': 1, 'detail': 'One line of evidence'}]}


def wire(provider, raw):
    if provider == 'claude':
        return ('{"type":"result","subtype":"success","is_error":false,'
                '"session_id":"fixture","modelUsage":{},"structured_output":' + raw + '}')
    return '\n'.join(map(json.dumps, [
        {'type': 'thread.started', 'thread_id': 'fixture'}, {'type': 'turn.started'},
        {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': raw}},
        {'type': 'turn.completed', 'usage': {}}]))


def install_peer(monkeypatch, provider, raw, observed, *, structured=True, failure=None):
    def factory(*args, **kwargs):
        def runner(argv, prompt, **options):
            request = json.loads(prompt.split('\n', 1)[1])
            turn = json.loads(request['attempt']['task']['objective'])
            schema = (json.loads(argv[argv.index('--json-schema') + 1]) if provider == 'claude'
                      else json.loads(Path(argv[argv.index('--output-schema') + 1]).read_text()))
            if structured:
                assert schema['required'] == ['verdict', 'summary', 'evidence']
                assert schema['properties']['evidence']['items']['properties']['path']['enum'] == ['x.py']
                assert turn['native_response_profile'] == c.NATIVE_RESPONSE_PROFILE
                assert 'JSON inside the outer text' not in prompt
            else:
                assert schema == TEXT_SCHEMA
                assert 'native_response_profile' not in turn
                assert 'JSON inside the outer text' in prompt
            observed.append((copy.deepcopy(turn), options))
            return ProcessResult(argv, -9 if failure else 0, wire(provider, raw), '', failure)
        return NativeExchange(*args, **kwargs, runner=runner)
    monkeypatch.setattr(c, 'NativeExchange', factory)


@pytest.mark.parametrize('provider', ['claude', 'codex'])
def test_native_direct_answer_uses_schema_and_retains_host_evidence(tmp_path, monkeypatch, provider):
    directory, record = prepare(tmp_path, provider)
    calls = []
    install_peer(monkeypatch, provider, json.dumps(payload()), calls)
    result = c.run(directory, record['contract_digest'], allow_external=True, allow_native=True)
    assert result['status'] == 'completed', result['answers']
    assert result['answers'][0]['answer'] == payload()
    assert calls[0][1]['timeout'] == 600 and calls[0][1]['max_output_bytes'] == 65536
    assert result['events'][0]['request_digest'] == digest(calls[0][0])
    assert result['contract'] == record['contract']
    with pytest.raises(ValueError, match='Terminal'):
        c.run(directory, record['contract_digest'], allow_external=True, allow_native=True)
    assert len(calls) == 1


@pytest.mark.parametrize('provider', ['claude', 'codex'])
@pytest.mark.parametrize('case', ['nested', 'malformed', 'duplicate', 'array', 'verdict',
                                 'extra', 'path', 'line', 'oversized'])
def test_direct_answer_refuses_invalid_evidence_without_retry(tmp_path, monkeypatch, provider, case):
    directory, record = prepare(tmp_path, provider)
    value = payload()
    if case == 'nested': value = {'text': json.dumps(value)}
    elif case == 'array': value = []
    elif case == 'verdict': value['verdict'] = 'trusted'
    elif case == 'extra': value['authority'] = 'approved'
    elif case == 'path': value['evidence'][0]['path'] = '../outside.py'
    elif case == 'line': value['evidence'][0]['line'] = True
    elif case == 'oversized': value['summary'] = 'x' * 16385
    raw = json.dumps(value)
    if case == 'malformed': raw = raw[:-1]
    elif case == 'duplicate': raw = raw.replace('{', '{"verdict":"approve",', 1)
    calls = []
    install_peer(monkeypatch, provider, raw, calls)
    result = c.run(directory, record['contract_digest'], allow_external=True, allow_native=True)
    answer = result['answers'][0]
    assert result['status'] == answer['status'] == 'failed'
    assert answer['answer'] is None and answer['error']['effects'] == 'unknown'
    assert 'retry_basis' not in answer['error']
    assert answer['process']['stdout'] == wire(provider, raw)
    with pytest.raises(ValueError, match='Terminal'):
        c.run(directory, record['contract_digest'], allow_external=True, allow_native=True)
    assert len(calls) == 1


@pytest.mark.parametrize('legacy', [False, True])
def test_native_pause_replay_preserves_original_request_digests(tmp_path, monkeypatch, legacy):
    directory, record = prepare(tmp_path, two=True, legacy=legacy)
    calls = []
    value = {'text': json.dumps(payload())} if legacy else payload()
    install_peer(monkeypatch, 'codex', json.dumps(value), calls, structured=not legacy)
    first = c.run(directory, record['contract_digest'], allow_external=True, allow_native=True,
                  max_operations=1)
    assert first['status'] == 'paused'
    previous = c.load(directory)['events'][0]
    final = c.run(directory, record['contract_digest'], allow_external=True, allow_native=True)
    assert final['status'] == 'completed' and len(calls) == 2
    assert final['events'][0] == previous
    assert final['contract'] == record['contract']
    assert final['events'][0]['request_digest'] == digest(calls[0][0])
    if legacy:
        assert set(calls[0][0]) == {'attempt_id', 'contract_digest', 'participant', 'round',
                                  'question', 'snapshot', 'previous_rounds'}


@pytest.mark.parametrize('marker', [None, False, 1, 'unknown', {}])
def test_unknown_profile_refuses_before_dispatch(tmp_path, marker):
    directory, record = prepare(tmp_path)
    record['contract']['native_response_profile'] = marker
    record['contract_digest'] = digest(record['contract'])
    store = RunStore(directory, existing=True)
    with store.lease():
        store.save(record)
    with pytest.raises(ValueError, match='response profile'):
        c.run(directory, record['contract_digest'], allow_external=True, allow_native=True,
              dispatcher=lambda *args: pytest.fail('dispatched'))


@pytest.mark.parametrize('provider', ['claude', 'codex'])
@pytest.mark.parametrize('timeout', [0, True, 601, float('nan'), float('inf')])
def test_native_timeout_refusals(provider, timeout):
    with pytest.raises(ValueError, match='timeout'):
        c.configuration(configuration(provider, timeout), 'source-review')


@pytest.mark.parametrize('adapter', ['command', 'antigravity'])
def test_other_adapter_timeout_bound_is_unchanged(adapter):
    cfg = configuration(adapter, 300)
    seat = cfg['participants']['reviewer']
    if adapter == 'command': seat['command'] = ['unused']
    else:
        seat['identity']['provider'] = 'google-antigravity'
        seat['effort'] = 'high'
    c.configuration(cfg, 'source-review')
    seat['timeout'] = 301
    with pytest.raises(ValueError, match='1..300'):
        c.configuration(cfg, 'source-review')


@pytest.mark.parametrize('failure', ['timeout_effects_unknown', 'cancelled_effects_unknown'])
def test_structured_failure_retains_unknown_effects_without_retry(tmp_path, monkeypatch, failure):
    directory, record = prepare(tmp_path)
    calls = []
    install_peer(monkeypatch, 'codex', json.dumps(payload()), calls, failure=failure)
    result = c.run(directory, record['contract_digest'], allow_external=True, allow_native=True)
    answer = result['answers'][0]
    assert result['status'] == ('cancelled' if failure.startswith('cancelled') else 'failed')
    assert answer['error']['failure'] == failure and answer['error']['effects'] == 'unknown'
    assert 'retry_basis' not in answer['error']
    assert len(calls) == 1
