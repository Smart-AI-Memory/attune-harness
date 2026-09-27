"""Saved memory CLI uses the durable owner and safe structured failures."""
# qualify: platform
import json
import os

import pytest

from attune_harness.memory_cli import main


def invoke(capsys, config, *args):
    code = main(['--config', str(config), 'saved', *map(str, args)])
    return code, json.loads(capsys.readouterr().out)


def dump(path, value):
    path.write_text(json.dumps(value))
    return path


def configured_store(tmp_path):
    config = dump(tmp_path / 'config.json', {'saved': {'root': str(tmp_path / 'store')}})
    scope = dump(tmp_path / 'scope.json', {'kind': 'global'})
    return config, scope


@pytest.mark.skipif(os.name != 'posix', reason='Saved file store is POSIX-only')
def test_all_saved_commands(tmp_path, capsys):
    config, scope = configured_store(tmp_path)
    request = dump(tmp_path / 'request.json', dict(request_id='save1', kind='memory',
        scope={'kind': 'global'}, title='Context', content='old content',
        source={'author': 'caller', 'reference': 'explicit request'}))
    code, result = invoke(capsys, config, 'save', '--request', request)
    assert code == 0
    identifier = result['record']['id']
    assert invoke(capsys, config, 'save', '--request', request)[1] == result
    assert invoke(capsys, config, 'show', identifier, '--scope', scope)[1]['content'] == 'old content'
    assert 'history' not in invoke(capsys, config, 'show', identifier, '--scope', scope)[1]
    assert len(invoke(capsys, config, 'list', '--scope', scope)[1]['records']) == 1
    assert len(invoke(capsys, config, 'search', 'content', '--scope', scope)[1]['records']) == 1
    dump(request, dict(request_id='revise1', scope={'kind': 'global'}, expected_revision=1,
                       changes={'content': 'new content'}))
    assert invoke(capsys, config, 'revise', identifier, '--request', request)[1]['record']['revision'] == 2
    dump(request, dict(request_id='forget1', scope={'kind': 'global'}, expected_revision=2))
    assert invoke(capsys, config, 'forget', identifier, '--request', request)[1]['record']['status'] == 'withdrawn'
    assert invoke(capsys, config, 'show', identifier, '--scope', scope)[0] == 2
    assert invoke(capsys, config, 'show', identifier, '--scope', scope, '--history')[1]['history']
    assert invoke(capsys, config, 'search', 'content', '--scope', scope)[1]['records'] == []
    assert invoke(capsys, config, 'reindex', '--scope', scope)[0] == 0
    dump(request, dict(request_id='task1', kind='task', scope={'kind': 'global'}, title='Task',
        content='Intent', next_action='Review', source={'author': 'caller', 'reference': 'explicit'}))
    task = invoke(capsys, config, 'save', '--request', request)[1]['record']['id']
    dump(request, dict(request_id='complete1', scope={'kind': 'global'}, expected_revision=1))
    assert invoke(capsys, config, 'complete', task, '--request', request)[1]['record']['status'] == 'completed'


@pytest.mark.skipif(os.name != 'posix', reason='Saved file store is POSIX-only')
def test_missing_redis_is_pending_and_request_errors_redacted(tmp_path, capsys, monkeypatch):
    config, scope = configured_store(tmp_path)
    monkeypatch.delenv('UNSET_SAVED_TEST_REDIS', raising=False)
    dump(config, {'saved': {'root': str(tmp_path / 'store'),
                          'redis': {'url_env': 'UNSET_SAVED_TEST_REDIS', 'namespace': 'test'}}})
    request = dump(tmp_path / 'request.json', dict(request_id='save1', kind='memory', scope={'kind': 'global'},
        title='Context', content='Retained', source={'author': 'caller', 'reference': 'explicit'}))
    code, result = invoke(capsys, config, 'save', '--request', request)
    assert code == 0 and result['index_status'] == 'pending'
    assert invoke(capsys, config, 'show', result['record']['id'], '--scope', scope)[1]['content'] == 'Retained'
    request.write_text('not JSON redis://private-password@host')
    code, result = invoke(capsys, config, 'save', '--request', request)
    assert code == 2 and 'private-password' not in json.dumps(result)


def test_invalid_configuration_is_structured(tmp_path, capsys):
    config, scope = configured_store(tmp_path)
    dump(config, {'saved': {'root': '../outside'}})
    code, result = invoke(capsys, config, 'list', '--scope', scope)
    assert code == 2 and result['status'] == 'failed'


@pytest.mark.skipif(os.name == 'posix', reason='Non-POSIX refusal')
def test_non_posix_store_refuses_before_write(tmp_path, capsys):
    config, scope = configured_store(tmp_path)
    code, result = invoke(capsys, config, 'list', '--scope', scope)
    assert code == 2 and result['status'] == 'failed'
    assert not (tmp_path / 'store').exists()
