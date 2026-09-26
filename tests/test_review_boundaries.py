import json
import sys
from pathlib import Path

import pytest

from attune_harness import review_participants as participants
from attune_harness.native import NativeExchange
from attune_harness.process import ProcessResult
from attune_harness.review_contract import digest, load_registry, parse_json
from attune_harness.review_participants import ReviewExchange, decode_action
from attune_harness.review_store import PersistenceError, RunStore, inspect_run


@pytest.mark.parametrize('raw', ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '[', 'x'])
def test_strict_json_rejects_ambiguous_input(raw):
    with pytest.raises(ValueError):
        parse_json(raw)


def test_utf8_limit_is_bytes():
    with pytest.raises(ValueError, match='byte limit'):
        parse_json('"é"', 3)


@pytest.mark.parametrize('update', [
    lambda d: d.update(schema_version=True),
    lambda d: d.update(request_digest='old-turn'),
    lambda d: d.update(extra=True),
    lambda d: d.update(action={'kind': 'final', 'text': ''}),
    lambda d: d.update(action={'kind': 'final', 'text': 'x' * 32769}),
    lambda d: d.update(action={'kind': 'final', 'text': 'ok', 'grants': ['shell']}),
    lambda d: d.update(action={'kind': 'tool', 'name': 'verify', 'arguments': []}),
    lambda d: d.update(action={'kind': 'other'}),
    lambda d: d.update(action=[]),
])
def test_bad_action_cannot_be_accepted(update):
    data = {'schema_version': 1, 'request_digest': 'current', 'action': {'kind': 'final', 'text': 'ok'}}
    update(data)
    with pytest.raises(ValueError):
        decode_action(json.dumps(data), 'current')


@pytest.mark.parametrize('update', [
    lambda d: d.update(schema_version=2),
    lambda d: d['participants'].pop('beta'),
    lambda d: d['participants'].update({'bad/name': d['participants'].pop('alpha')}),
    lambda d: d['participants']['alpha'].update(adapter='unsupported'),
    lambda d: d['participants']['alpha'].update(tools=['retrieve', 'retrieve']),
    lambda d: d['participants']['alpha'].update(tools=['shell']),
    lambda d: d['participants']['alpha'].update(max_turns=0),
    lambda d: d['participants']['alpha'].update(max_tool_calls=True),
    lambda d: d['participants']['alpha'].update(extra=1),
    lambda d: d['participants']['alpha'].update(adapter='command', command='shell text', timeout=2),
    lambda d: d['participants']['alpha'].update(adapter='command', command=[''], timeout=2),
    lambda d: d['participants']['alpha'].update(adapter='claude', model='', timeout=2),
    lambda d: d['participants']['alpha'].update(adapter='codex', model='chosen', timeout=True),
])
def test_invalid_registry_is_not_available(tmp_path, update):
    from attune_harness.features import FeatureUnavailable
    data = {'schema_version': 1, 'participants': {
        name: {'adapter': 'deterministic', 'tools': ['verify'], 'max_turns': 3, 'max_tool_calls': 1}
        for name in ('alpha', 'beta')
    }}
    update(data)
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises((ValueError, FeatureUnavailable)):
        load_registry(path)


def wire():
    turn = {'task_id': 'task', 'attempt_id': 'attempt', 'turn_id': 'turn', 'role': 'lead',
            'participant_id': 'configured', 'requirement_revision': 'revision',
            'query': 'quartz', 'history': [], 'tools': []}
    return json.dumps({'schema_version': 1, 'request_digest': digest(turn), 'turn': turn})


@pytest.mark.parametrize('provider', ['claude', 'codex'])
def test_native_turn_uses_real_translator_with_injected_process(provider, tmp_path, monkeypatch):
    calls = []
    def factory(name, **kwargs):
        return NativeExchange(name, **kwargs, runner=runner)
    def runner(argv, prompt, **kwargs):
        calls.append(argv)
        attempt = json.loads(prompt.split('\n', 1)[1])['attempt']
        request = json.loads(attempt['task']['objective'])
        action = {'schema_version': 1, 'request_digest': request['request_digest'],
                  'action': {'kind': 'tool', 'name': 'verify', 'arguments': {}}}
        output = {'text': json.dumps(action)}
        if provider == 'claude':
            raw = json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,
                              'session_id': 'fixture-session', 'structured_output': output,
                              'modelUsage': {'reported-model': {}}})
        else:
            raw = '\n'.join(json.dumps(event) for event in [
                {'type': 'thread.started', 'thread_id': 'fixture-session'},
                {'type': 'turn.started'},
                {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(output)}},
                {'type': 'turn.completed', 'usage': {}},
            ])
        return ProcessResult(argv, 0, raw, '', None)
    monkeypatch.setattr(participants, 'NativeExchange', factory)
    exchange = ReviewExchange({'adapter': provider, 'model': 'requested-model', 'timeout': 2}, tmp_path)
    raw = wire()
    action = decode_action(exchange(raw), json.loads(raw)['request_digest'])
    assert action['name'] == 'verify'
    assert calls[0][calls[0].index('--model') + 1] == 'requested-model'
    assert exchange.last_identity['reported']['session_id'] == 'fixture-session'
    assert exchange.last_identity['requested_model'] == 'requested-model'


def test_command_roundtrip_uses_argument_vector_and_stdin(tmp_path):
    program = ('import json,sys; d=json.load(sys.stdin); '
               'print(json.dumps(dict(schema_version=1,request_digest=d["request_digest"],'
               'action=dict(kind="final",text=sys.argv[1]))))')
    literal = 'literal $(touch unwanted) ; echo no'
    exchange = ReviewExchange({'adapter': 'command', 'command': [sys.executable, '-c', program, literal],
                               'timeout': 2}, tmp_path)
    raw = wire()
    assert decode_action(exchange(raw), json.loads(raw)['request_digest'])['text'] == literal
    assert not (tmp_path / 'unwanted').exists()
    assert exchange.last_identity['returncode'] == 0


@pytest.mark.parametrize('command,match,timeout', [
    (['/does/not/exist'], 'not_found', 2),
    ([sys.executable, '-c', 'import sys; sys.stderr.write("diagnostic"); sys.exit(3)'], 'diagnostic', 2),
    ([sys.executable, '-c', 'import time; time.sleep(3)'], 'timeout', 0.03),
    ([sys.executable, '-c', 'print("x"*70000)'], 'output_limit', 2),
])
def test_command_faults_do_not_become_output(tmp_path, command, match, timeout):
    exchange = ReviewExchange({'adapter': 'command', 'command': command, 'timeout': timeout}, tmp_path)
    with pytest.raises(RuntimeError, match=match):
        exchange(wire())


def test_store_failure_preserves_previous_record(tmp_path, monkeypatch):
    from attune_harness import review_store
    store = RunStore(tmp_path / 'run')
    before = {'schema_version': 1, 'operation': 'review', 'status': 'running', 'future_field': {'keep': True}}
    store.save(before)
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(review_store.os, 'replace', fail)
    with pytest.raises(PersistenceError):
        store.save({**before, 'status': 'completed'})
    assert json.loads(store.path.read_text(encoding='utf-8')) == before
    assert list(store.directory.iterdir()) == [store.path]
    inspected = inspect_run(store.directory)
    assert inspected['status'] == 'unresolved'
    assert inspected['future_field'] == before['future_field']
    assert json.loads(store.path.read_text(encoding='utf-8')) == before


def test_store_rejects_metadata_and_symlink(tmp_path):
    with pytest.raises(ValueError):
        RunStore(tmp_path / '.git')
    linked = tmp_path / 'linked'
    linked.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        RunStore(linked)


@pytest.mark.parametrize('record', [[], {'schema_version': 2}, {'schema_version': 1, 'operation': 'other', 'status': 'completed'}])
def test_inspection_rejects_incompatible_record(tmp_path, record):
    (tmp_path / 'record.json').write_text(json.dumps(record), encoding='utf-8')
    with pytest.raises(ValueError):
        inspect_run(tmp_path)


@pytest.mark.parametrize('profile,role', [('feature-build-v1', 'worker'),
    ('feature-build-v1', 'reviewer'), ('feature-planning-v1', 'planner')])
@pytest.mark.parametrize('provider', ['claude', 'codex'])
def test_only_codex_build_proposals_isolate_user_integrations(tmp_path, monkeypatch, profile, role, provider):
    observed = []
    def runner(argv, prompt, **kwargs):
        observed.append(argv)
        output = {'text': 'A bounded proposal'}
        if provider == 'claude':
            raw = json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,
                              'session_id': 'fixture', 'structured_output': output})
        else:
            raw = '\n'.join(json.dumps(event) for event in [
                {'type': 'thread.started', 'thread_id': 'fixture'}, {'type': 'turn.started'},
                {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(output)}},
                {'type': 'turn.completed'}])
        return ProcessResult(argv, 0, raw, '')
    monkeypatch.setattr(participants, 'NativeExchange',
                        lambda name, **kwargs: NativeExchange(name, **kwargs, runner=runner))
    data = json.loads(wire())
    data['turn'].update(operation_profile=profile, role=role, protocol='Return proposal')
    data['request_digest'] = digest(data['turn'])
    exchange = ReviewExchange({'adapter': provider, 'model': 'requested-model', 'timeout': 2,
                               'tools': []}, tmp_path, profile=profile)
    assert decode_action(exchange(json.dumps(data)), data['request_digest'])['text'] == 'A bounded proposal'
    isolated = profile == 'feature-build-v1' and provider == 'codex'
    assert ('--ignore-user-config' in observed[0]) is isolated
    assert exchange.last_identity.get('user_config_policy') == ('requested_isolation' if isolated else None)
