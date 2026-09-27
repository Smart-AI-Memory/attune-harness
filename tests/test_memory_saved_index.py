"""Saved Redis projection is optional, bounded, isolated and secret-safe."""
# qualify: platform
import json
import sys
import types

import pytest

from attune_harness.memory_saved_index import RedisSavedIndex


def test_lazy_client_scoped_keys_and_bounds(monkeypatch):
    calls = []
    class Client:
        def set(self, key, value):
            calls.append(('set', key, json.loads(value)))
        def delete(self, key):
            calls.append(('delete', key))
    class Redis:
        @staticmethod
        def from_url(url, **kwargs):
            calls.append(('connect', url, kwargs))
            return Client()
    monkeypatch.setitem(sys.modules, 'redis', types.SimpleNamespace(Redis=Redis))
    monkeypatch.setenv('SAVED_TEST_REDIS', 'redis://secret@localhost')
    index = RedisSavedIndex({'url_env': 'SAVED_TEST_REDIS', 'namespace': 'tests'})
    assert calls == []
    record = {'id': 'abc', 'scope': {'kind': 'global'}, 'content': 'hello'}
    index.upsert(record)
    index.remove(record['id'], record['scope'])
    assert calls[0][2] == dict(socket_connect_timeout=1.0, socket_timeout=1.0,
                              retry_on_timeout=False, decode_responses=True)
    assert calls[1][1] == calls[2][1]
    assert calls[1][1].startswith('attune:harness:saved:v1:tests:')
    assert index._key('abc', {'kind': 'global'}) != index._key('abc', {'kind': 'project', 'project': '/x'})
    assert index._key('abc', {'kind': 'global'}) != index._key('def', {'kind': 'global'})


def test_missing_env_and_connection_errors_are_redacted(monkeypatch):
    monkeypatch.delenv('SAVED_TEST_REDIS', raising=False)
    index = RedisSavedIndex({'url_env': 'SAVED_TEST_REDIS', 'namespace': 'tests'})
    record = {'id': 'abc', 'scope': {'kind': 'global'}}
    with pytest.raises(RuntimeError, match='pending'):
        index.upsert(record)
    class Client:
        def delete(self, key):
            raise OSError('redis://secret-password@host')
    index._client = Client()
    with pytest.raises(RuntimeError) as caught:
        index.remove('abc', record['scope'])
    assert 'secret-password' not in str(caught.value)


@pytest.mark.parametrize('config', [{}, {'url_env': 'BAD-NAME', 'namespace': 'x'},
    {'url_env': 'ENV', 'namespace': '../escape'}, {'url_env': 'ENV', 'namespace': 'x', 'url': 'secret'}])
def test_invalid_config(config):
    with pytest.raises(ValueError):
        RedisSavedIndex(config)


def test_url_query_cannot_override_network_bounds(monkeypatch):
    monkeypatch.setenv('SAVED_TEST_REDIS',
                       'redis://secret@localhost/0?socket_timeout=600&socket_connect_timeout=600')
    index = RedisSavedIndex({'url_env': 'SAVED_TEST_REDIS', 'namespace': 'tests'})
    with pytest.raises(RuntimeError, match='pending'):
        index.upsert({'id': 'abc', 'scope': {'kind': 'global'}})
    assert index._client is None
