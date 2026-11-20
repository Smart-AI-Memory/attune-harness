"""Saved-memory and task lifecycle through fresh installed CLI shell processes.

Windows qualification runs PowerShell 5.1 and 7 with Python 3.12. Other
platforms run the same sequence as a control. These are lifecycle witnesses;
concurrency, crash recovery and power-loss durability retain separate evidence.
"""
# qualify: platform

import importlib.metadata
import json
import os
import sys
from uuid import UUID

import pytest

from attune_harness.task_contract import create_task
from test_review import case
from test_windows_task_journey import file_bytes, run_cli


@pytest.mark.parametrize('engine', ['powershell.exe', 'pwsh.exe'] if os.name == 'nt' else ['posix-control'])
@pytest.mark.parametrize('directory_name', ['plain', "space's $literal` café 雪"])
def test_saved_memory_and_task_lifecycle(tmp_path, monkeypatch, engine, directory_name, case,
                                         record_property):
    """Retain history, replay snapshots and pending reviews across real CLI restarts."""
    home = tmp_path.resolve(strict=True) / directory_name
    home.mkdir()
    inputs = home / 'inputs'
    inputs.mkdir()
    root = home / 'managed suffix' / 'private store'
    state = root / 'state.json'
    scope = {'kind': 'global'}

    def document(name, value):
        path = inputs / (name + '.json')
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return str(path)

    config = document('config', {'saved': {'root': str(root)}})
    scope_file = document('scope', scope)
    record_property('shell', engine)
    record_property('python', sys.version)
    record_property('harness', importlib.metadata.version('attune-harness'))

    # Guard the actual CLI child, including swallowed optional-index failures.
    guard = home / 'offline-guard'
    guard.mkdir()
    started, denied = guard / 'started.txt', guard / 'denied.txt'
    (guard / 'sitecustomize.py').write_text(
        'import socket\nfrom pathlib import Path\n'
        'def forbidden(*args, **kwargs):\n'
        f'    with Path({str(denied)!r}).open("ab") as log: log.write(b"denied\\n")\n'
        '    raise AssertionError("Offline saved journey attempted network access")\n'
        'socket.socket.connect = forbidden\nsocket.socket.connect_ex = forbidden\n'
        'socket.create_connection = forbidden\nsocket.getaddrinfo = forbidden\n'
        f'with Path({str(started)!r}).open("ab") as log: log.write(b"guarded\\n")\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('PYTHONPATH', str(guard))
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1')
    index_env = 'HARNESS_SAVED_JOURNEY_REDIS'
    monkeypatch.delenv(index_env, raising=False)
    calls = 0

    def saved(*arguments, expected_code=0, read_only=False):
        nonlocal calls
        before_inputs = file_bytes(inputs)
        before_state = (state.read_bytes(), state.stat().st_mtime_ns) if read_only else None
        code, result, output = run_cli(['memory', '--config', config, 'saved', *arguments], home, engine)
        calls += 1
        assert code == expected_code and result, output
        assert started.read_bytes().splitlines() == [b'guarded'] * calls
        assert not denied.exists(), 'The CLI attempted network access'
        assert file_bytes(inputs) == before_inputs
        if read_only:
            assert (state.read_bytes(), state.stat().st_mtime_ns) == before_state
        return result

    original = {'request_id': 'memory-save', 'kind': 'memory', 'scope': scope,
                'title': 'Résumé café 雪', 'content': 'Acceptance Ω "quoted" $literal` evidence.\r\n',
                'source': {'author': 'caller', 'reference': 'Explicit saved request'}}
    save_file = document('memory-save', original)
    first = saved('save', '--request', save_file)
    record = first['record']
    identity = record['id']
    assert str(UUID(identity)) == identity
    assert record['revision'] == 1 and record['status'] == 'active' and len(record['history']) == 1
    assert record['title'] == original['title'] and record['content'] == original['content']
    assert first['index_status'] == 'disabled'
    assert saved('save', '--request', save_file, read_only=True) == first
    shown = saved('show', identity, '--scope', scope_file, read_only=True)
    assert shown['content'] == original['content'] and 'history' not in shown
    assert [r['id'] for r in saved('list', '--scope', scope_file, read_only=True)['records']] == [identity]
    assert [r['id'] for r in saved('search', 'Acceptance Ω', '--scope', scope_file,
                                 read_only=True)['records']] == [identity]
    assert saved('reindex', '--scope', scope_file, read_only=True) == {
        'index_status': 'disabled', 'indexed': 0, 'pending': 0}

    revised_content = 'Revised acceptance café 雪 $literal` evidence.'
    revise_file = document('memory-revise', {'request_id': 'memory-revise', 'scope': scope,
        'expected_revision': 1, 'changes': {'content': revised_content}})
    revised = saved('revise', identity, '--request', revise_file)
    assert revised['record']['revision'] == 2 and revised['record']['content'] == revised_content
    assert [h['operation'] for h in revised['record']['history']] == ['save', 'revise']
    stale = document('stale-revise', {'request_id': 'stale-revise', 'scope': scope,
        'expected_revision': 1, 'changes': {'content': 'Must not overwrite revision 2'}})
    assert saved('revise', identity, '--request', stale, expected_code=2,
                 read_only=True)['error'] == 'conflict'
    forget_file = document('memory-forget', {'request_id': 'memory-forget', 'scope': scope,
                                            'expected_revision': 2})
    forgotten = saved('forget', identity, '--request', forget_file)['record']
    assert forgotten['revision'] == 3 and forgotten['status'] == 'withdrawn'
    assert saved('save', '--request', save_file, read_only=True) == first
    assert saved('show', identity, '--scope', scope_file, expected_code=2,
                 read_only=True)['error'] == 'not_found'
    assert saved('list', '--scope', scope_file, read_only=True)['records'] == []
    assert saved('search', 'acceptance', '--scope', scope_file, read_only=True)['records'] == []
    withdrawn = saved('show', identity, '--scope', scope_file, '--history', read_only=True)
    assert withdrawn['status'] == 'withdrawn' and withdrawn['revision'] == 3
    assert [h['operation'] for h in withdrawn['history']] == ['save', 'revise', 'forget']
    changed_file = document('changed-save', dict(original, content='Different input with the same ID'))
    assert saved('save', '--request', changed_file, expected_code=2,
                 read_only=True)['error'] == 'conflict'

    pending = {'status': 'pending', 'goal': 'Review saved acceptance', 'progress': 'Retained café 雪',
               'evidence': ['Explicit fixture reference'], 'reason': 'Deferred review',
               'next_action': 'Inspect the retained evidence'}
    task_file = document('task-save', {'request_id': 'task-save', 'kind': 'task', 'scope': scope,
        'title': 'Review task', 'content': 'Retain pending review', 'next_action': 'Review evidence',
        'source': original['source'], 'opportunity_review': pending})
    task = saved('save', '--request', task_file)['record']
    complete_file = document('task-complete', {'request_id': 'task-complete', 'scope': scope,
                                             'expected_revision': task['revision']})
    completed = saved('complete', task['id'], '--request', complete_file)['record']
    assert completed['status'] == 'completed' and completed['revision'] == 2
    assert completed['opportunity_review'] == pending
    assert completed['history'][-1]['record']['opportunity_review'] == pending
    assert saved('complete', task['id'], '--request', complete_file, read_only=True)['record'] == completed
    discovered = saved('list', '--scope', scope_file, '--pending-review', read_only=True)['records']
    assert [r['id'] for r in discovered] == [task['id']]
    assert discovered[0]['status'] == 'completed' and discovered[0]['opportunity_review'] == pending
    assert pending['next_action'] in discovered[0]['opportunity_review_notice']

    # A real draft execution owner remains read-only; saving intent never dispatches it.
    owner = create_task(case[0].parent, case[1], goal='Inspect linked saved intent',
                        directory=home / 'execution-owner')
    owner_before = file_bytes(home / 'execution-owner')
    project_scope = {'kind': 'project', 'project': owner['request']['project_root']}
    project_scope_file = document('project-scope', project_scope)
    linked_file = document('linked-save', {'request_id': 'linked-save', 'kind': 'task',
        'scope': project_scope, 'title': 'Linked intent', 'content': 'Inspect the existing owner',
        'next_action': 'Inspect status', 'source': original['source'], 'opportunity_review': pending,
        'execution': {'directory': str(home / 'execution-owner'), 'task_id': owner['request']['task_id']}})
    linked = saved('save', '--request', linked_file)['record']
    observed = saved('show', linked['id'], '--scope', project_scope_file, read_only=True)
    assert observed['execution_status'] == owner['status'] == 'draft'
    assert 'execution_status' not in linked
    assert saved('show', linked['id'], '--scope', scope_file, expected_code=2,
                 read_only=True)['error'] == 'not_found'
    linked_complete = document('linked-complete', {'request_id': 'linked-complete',
        'scope': project_scope, 'expected_revision': linked['revision']})
    assert saved('complete', linked['id'], '--request', linked_complete, expected_code=2,
                 read_only=True)['error'] == 'invalid'
    assert [r['id'] for r in saved('list', '--scope', scope_file, '--pending-review',
                                 read_only=True)['records']] == [task['id']]
    assert file_bytes(home / 'execution-owner') == owner_before

    config = document('unavailable-index', {'saved': {'root': str(root),
        'redis': {'url_env': index_env, 'namespace': 'saved-journey'}}})
    pending_file = document('pending-save', dict(original, request_id='pending-save'))
    unindexed = saved('save', '--request', pending_file)
    assert unindexed['index_status'] == 'pending'
    current = saved('show', unindexed['record']['id'], '--scope', scope_file, read_only=True)
    assert current['content'] == original['content'] and current['index_status'] == 'pending'
    before_reindex = json.loads(state.read_bytes())
    assert saved('reindex', '--scope', scope_file) == {'index_status': 'pending', 'indexed': 0, 'pending': 3}
    after_reindex = json.loads(state.read_bytes())
    assert after_reindex['records'] == before_reindex['records']
    assert after_reindex['operations'] == before_reindex['operations']
    replay = saved('save', '--request', save_file, read_only=True)
    assert replay['record'] == first['record'] and replay['index_status'] == 'pending'
    visible = saved('list', '--scope', scope_file, read_only=True)['records']
    assert {r['id'] for r in visible} == {task['id'], unindexed['record']['id']}
    assert all(r['index_status'] == 'pending' for r in visible)
    assert file_bytes(home / 'execution-owner') == owner_before
    assert after_reindex['schema_version'] == 1 and len(after_reindex['records']) == 4
    assert len(after_reindex['operations']) == 7
    record_property('guarded_cli_processes', calls)
    record_property('denied_network_attempts', 0)
