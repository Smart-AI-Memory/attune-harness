"""Behavioral journeys at the durable, host-owned dispatch boundary."""
# qualify: platform

import copy
import json
from pathlib import Path
from threading import Event

import pytest

from attune_harness import consultation as c
from attune_harness.cli import main
from attune_harness.review_store import RunStore


def config(operation='source-review'):
    seats = {'reviewer': {'adapter': 'command', 'identity': {'provider': 'other', 'model': 'review-1'},
                           'timeout': 10, 'command': ['unused']}}
    if operation == 'roundtable':
        seats['critic'] = {'adapter': 'command', 'identity': {'provider': 'third', 'model': 'critic-1'},
                           'timeout': 10, 'command': ['unused']}
    return {'schema_version': 1, 'question': 'Inspect the boundary',
            'author': {'provider': 'codex', 'model': 'gpt-6.1-sol'},
            'participants': seats, 'rounds': 1 if operation == 'source-review' else 2}


def prepared(tmp_path, operation='source-review'):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'x.py').write_text('x = 1\n')
    directory = tmp_path / 'run'
    record = c.prepare(operation, root, ['x.py'], config(operation), directory)
    return root, directory, record


def completed(*args):
    return {'status': 'completed', 'answer': {'verdict': 'uncertain', 'summary': 'No claim', 'evidence': []},
            'identity': {'authenticated_model': False}, 'error': None, 'process': None}


def test_roundtable_independence_pause_replay_and_frozen_bytes(tmp_path):
    root, directory, record = prepared(tmp_path, 'roundtable')
    (root / 'x.py').write_text('changed after prepare')
    seen = []
    def dispatch(seat, turn, *args):
        seen.append(copy.deepcopy(turn))
        assert turn['snapshot']['files']['x.py']['text'] == 'x = 1\n'
        return completed()
    first = c.run(directory, record['contract_digest'], allow_external=True,
                  max_operations=1, dispatcher=dispatch)
    assert first['status'] == 'paused'
    assert len(first['answers']) == 1
    final = c.run(directory, record['contract_digest'], allow_external=True, dispatcher=dispatch)
    assert final['status'] == 'completed'
    assert len(seen) == 4
    assert [len(t['previous_rounds']) for t in seen] == [0, 0, 2, 2]
    assert all('process' not in a for t in seen for a in t['previous_rounds'])
    assert len(final['answers']) == 4
    assert len(final['events']) == 4
    with pytest.raises(ValueError, match='Terminal'):
        c.run(directory, record['contract_digest'], allow_external=True, dispatcher=dispatch)
    assert len(seen) == 4


def test_consumed_before_dispatch_and_unknown_turn_never_repeats(tmp_path):
    _, directory, record = prepared(tmp_path)
    calls = []
    def interrupt(*args):
        calls.append(1)
        persisted = c.load(directory)
        assert persisted['events'][0]['phase'] == 'dispatching'
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        c.run(directory, record['contract_digest'], allow_external=True, dispatcher=interrupt)
    assert c.load(directory)['status'] == 'unresolved'
    with pytest.raises(RuntimeError, match='reconcile'):
        c.run(directory, record['contract_digest'], allow_external=True, dispatcher=interrupt)
    assert len(calls) == 1
    current = c.load(directory)
    with pytest.raises(ValueError, match='Stale'):
        c.abandon(directory, record['checkpoint_digest'])
    abandoned = c.abandon(directory, current['checkpoint_digest'])
    assert abandoned['abandonment']['effects'] == 'unknown'
    assert abandoned['events'][0]['phase'] == 'dispatching'


def test_missing_authority_stale_contract_and_copied_owner_do_not_dispatch(tmp_path):
    _, directory, record = prepared(tmp_path)
    for accept, external in [(record['contract_digest'], False), ('stale', True)]:
        with pytest.raises(ValueError):
            c.run(directory, accept, allow_external=external, dispatcher=lambda *a: pytest.fail('dispatch'))
    copied = tmp_path / 'copy'
    import shutil
    shutil.copytree(directory, copied)
    with pytest.raises(ValueError, match='Copied'):
        c.load(copied)
    assert c.load(directory)['events'] == []


def test_native_authority_and_pre_cancel(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'x.py').write_text('x=1')
    cfg = config()
    cfg['participants']['reviewer'] = {'adapter': 'claude', 'identity': {'provider': 'claude', 'model': 'claude-opus-5-5'}, 'timeout': 1}
    directory = tmp_path / 'run'
    record = c.prepare('source-review', root, ['x.py'], cfg, directory)
    with pytest.raises(ValueError, match='native authority'):
        c.run(directory, record['contract_digest'], allow_external=True)
    cancel = Event()
    cancel.set()
    assert c.run(directory, record['contract_digest'], allow_external=True, allow_native=True,
                 cancel=cancel, dispatcher=lambda *a: pytest.fail('dispatch'))['status'] == 'cancelled'


@pytest.mark.parametrize('change', ['same_author', 'same_seats', 'rounds', 'timeout', 'alias'])
def test_configuration_refusals(change):
    operation = 'roundtable' if change == 'same_seats' else 'source-review'
    cfg = config(operation)
    if change == 'same_author':
        cfg['participants']['reviewer']['identity'] = cfg['author']
    elif change == 'same_seats':
        cfg['participants']['critic']['identity'] = cfg['participants']['reviewer']['identity']
    elif change == 'rounds':
        cfg['rounds'] = 2
    elif change == 'timeout':
        cfg['participants']['reviewer']['timeout'] = float('nan')
    else:
        cfg['participants']['reviewer']['identity']['model'] = 'opus'
    with pytest.raises(ValueError):
        c.configuration(cfg, operation)


def test_source_citations_are_host_checked(tmp_path):
    _, _, record = prepared(tmp_path)
    snapshot = record['contract']['snapshot']
    for path, line in [('outside', 1), ('x.py', 2), ('x.py', True)]:
        with pytest.raises(ValueError):
            c.answer(json.dumps({'verdict': 'approve', 'summary': 'claim',
                                 'evidence': [{'path': path, 'line': line, 'detail': 'why'}]}), snapshot)


def test_real_command_exchange_and_cli_journey(tmp_path, capsys):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'x.py').write_text('x=1\n')
    script = tmp_path / 'seat.py'
    script.write_text('''import hashlib,json,sys
raw=sys.stdin.read()
assert json.loads(raw)['attempt']['role']=='reviewer'
print(json.dumps({'version':1,'request_digest':hashlib.sha256(raw.encode()).hexdigest(),
'text':json.dumps({'verdict':'approve','summary':'Inspected','evidence':[{'path':'x.py','line':1,'detail':'Assignment'}]})}))
''')
    import sys
    cfg = config()
    cfg['participants']['reviewer']['command'] = [sys.executable, str(script)]
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(cfg))
    directory = tmp_path / 'run'
    assert main(['source-review', 'prepare', '--project', str(root), '--path', 'x.py',
                 '--config', str(config_file), '--run-dir', str(directory)]) == 0
    contract = json.loads(capsys.readouterr().out)['contract_digest']
    assert main(['roundtable', 'status', str(directory)]) == 2
    capsys.readouterr()
    assert main(['source-review', 'run', str(directory), '--accept', contract, '--allow-external']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['answers'][0]['answer']['verdict'] == 'approve'
    assert result['answers'][0]['identity']['reported'] is None
    assert main(['source-review', 'status', str(directory)]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'completed'


def test_failed_turn_stops_without_fallback(tmp_path):
    _, directory, record = prepared(tmp_path, 'roundtable')
    calls = []
    def failed(*args):
        calls.append(1)
        return {**completed(), 'status': 'failed', 'error': {'effects': 'unknown'}}
    result = c.run(directory, record['contract_digest'], allow_external=True, dispatcher=failed)
    assert result['status'] == 'failed'
    assert len(calls) == 1
    with pytest.raises(ValueError, match='Terminal'):
        c.run(directory, record['contract_digest'], allow_external=True, dispatcher=failed)


def test_writer_lease_blocks_concurrent_dispatch(tmp_path):
    _, directory, record = prepared(tmp_path)
    with RunStore(directory, existing=True).lease():
        with pytest.raises(OSError, match='busy'):
            c.run(directory, record['contract_digest'], allow_external=True, dispatcher=lambda *a: pytest.fail('dispatch'))


@pytest.mark.parametrize('mutation', ['remove_recovery', 'change_recovery', 'events', 'status', 'result'])
def test_checkpoint_changes_never_repeat_dispatch(tmp_path, mutation):
    _, directory, record = prepared(tmp_path)
    calls = []
    def dispatch(*args):
        calls.append(1)
        return completed()
    c.run(directory, record['contract_digest'], allow_external=True, max_operations=1, dispatcher=dispatch)
    path = directory / 'record.json'
    value = json.loads(path.read_text())
    if mutation == 'remove_recovery':
        value.pop('recovery')
        value['events'] = []
    elif mutation == 'change_recovery':
        value['recovery']['profile'] = 'another-profile'
    elif mutation == 'events':
        value['events'] = []
    elif mutation == 'status':
        value['status'] = 'prepared'
    else:
        value['events'][0]['result']['answer']['summary'] = 'Changed'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        c.run(directory, record['contract_digest'], allow_external=True, dispatcher=dispatch)
    assert len(calls) == 1


@pytest.mark.parametrize('reported,expected', [('requested-model', 'completed'), ('substituted-model', 'failed'), (None, 'completed')])
def test_native_requested_and_reported_identity_retained_without_substitution(tmp_path, monkeypatch, reported, expected):
    _, _, record = prepared(tmp_path)
    from attune_harness.native import NativeExchange
    from attune_harness.process import ProcessResult
    payload = {'verdict': 'uncertain', 'summary': 'Observed', 'evidence': []}
    def factory(*args, **kwargs):
        def runner(argv, prompt, **unused):
            envelope = {'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': 'session',
                        'modelUsage': {reported: {}} if reported else {},
                        'structured_output': {'text': json.dumps(payload)}}
            return ProcessResult(argv, 0, json.dumps(envelope), '')
        return NativeExchange(*args, runner=runner, **kwargs)
    monkeypatch.setattr(c, 'NativeExchange', factory)
    seat = {'adapter': 'claude', 'identity': {'provider': 'claude', 'model': 'requested-model'}, 'timeout': 1}
    turn = {'attempt_id': 'attempt', 'contract_digest': record['contract_digest'], 'participant': 'reviewer',
            'snapshot': record['contract']['snapshot']}
    result = c.dispatch(seat, turn, tmp_path, Event())
    assert result['status'] == expected
    assert result['identity']['configured']['model'] == 'requested-model'
    assert result['identity']['reported']['reported_models'] == ((reported,) if reported else ())
    assert result['identity']['authenticated_model'] is False
