"""Generation selection and read-time exclusion at the Redis boundary."""
# qualify: platform

from copy import deepcopy
import json
from pathlib import Path
import time

import pytest

from attune_harness import memory_hydration_redis as native, memory_redis
from attune_harness.memory_hydration_contract import function_digest, function_source, namespace
from attune_harness.memory_reader import NativeReader, roots_config
from attune_harness.review_contract import canonical
from test_memory_hydration_contract import FIXTURE
from test_memory_redis import FakeError, FakeRedis, INDEX, _library


def authority(tmp_path):
    roots = []
    for ident, tier in [('curated', 'curated'), ('personal', 'personal'), ('reference', 'personal')]:
        directory = tmp_path / ident
        directory.mkdir()
        roots.append(dict(id=ident, path=str(directory.resolve()), tier=tier, scope='demo',
                          owner='local-user', classification='internal'))
    return dict(schema_version=1, actor='local-user', owners=['local-user'], scopes=['demo'],
                classifications=['internal'], profiles=['offline'], roots=roots,
                redis=dict(url='redis://fixture/0', projection='harness-v1', dataset='demo'))


class GenerationRedis(FakeRedis):
    def __init__(self, config):
        super().__init__()
        self.manifest = {**deepcopy(FIXTURE['manifest']),
                         'binding': NativeReader(roots_config(config)).binding,
                         'function_digest': function_digest()}
        self.active = namespace('demo') + 'active'
        self.prefix = native.generation_prefix('demo', self.manifest['generation'])
        self.index = native.generation_index('demo', self.manifest['generation'])
        raw = canonical(self.manifest)
        self.strings = {self.active: raw, self.prefix + 'manifest': raw}
        self.hashes = {self.prefix + key: dict(record) for key, record in FIXTURE['records'].items()}
        for root in config['roots']:
            if root['id'] == 'personal':
                self.hashes[self.prefix + 'file:personal:note']['path'] = str(Path(root['path']) / 'note.md')
        self.hashes['attune:memory:node:foreign'] = dict(name='Aurora foreign', layer='curated', description='wrong namespace')
        self.sets = {self.prefix + 'status:active': set(FIXTURE['active'])}
        self.bundle = function_source()
        self.info = dict(index_name=self.index, index_definition=['key_type', 'HASH', 'prefixes',
                         [self.prefix + family + ':' for family in ('node', 'file', 'lesson', 'rule')]],
                         num_docs=5, indexing=0, hash_indexing_failures=0,
                         attributes=[['identifier', name, 'attribute', name, 'type', kind,
                                      *(['WEIGHT', '2'] if name == 'name' else [])]
                                     for name, kind in [('name', 'TEXT'), ('description', 'TEXT'), ('text', 'TEXT'),
                                                        ('updated_at', 'TEXT'), ('type', 'TAG'), ('status', 'TAG'),
                                                        ('layer', 'TAG'), ('corpus', 'TAG'), ('tags', 'TAG')]])
        self.switch_on_membership = False
        self.switch_on_node = False

    def hgetall(self, key):
        result = super().hgetall(key)
        if self.switch_on_node:
            self.strings[self.active] = 'changed'
        return result

    def execute_command(self, name, *args):
        self.calls.append((name, *args))
        if name == 'FT.INFO':
            assert args == (self.index,)
            return self.info
        if name == 'FUNCTION':
            assert args == ('LIST', 'LIBRARYNAME', native.LIBRARY, 'WITHCODE')
            return [['library_name', native.LIBRARY, 'library_code', self.bundle]]
        if name == 'FCALL_RO':
            function, key_count, prefix, argument = args
            assert key_count == 0 and prefix == self.prefix
            if function == 'harness_recall_digest_v1':
                return [json.dumps(dict(id=ident, **self.hashes[prefix + 'node:' + ident],
                                        edges=[json.dumps(edge) for edge in FIXTURE['edges'].get(ident, [])]))
                        for ident in ('aurora', 'retired')][:int(argument)]
            assert function == 'harness_recall_related_v1'
            suffix = argument if argument.startswith('file:') else 'node:' + argument
            record = self.hashes.get(prefix + suffix)
            return [json.dumps(dict(id=argument, **{key: value for key, value in record.items() if key != 'text'}))] if record else []
        if name == 'FT.SEARCH':
            assert args[0] == self.index
            return super()._search(INDEX, *args[1:])
        if name == 'SMISMEMBER':
            assert args[0] == self.prefix + 'status:active'
            if self.switch_on_membership:
                self.strings[self.active] = 'changed'
            return [int(ident in self.sets[args[0]]) for ident in args[1:]]
        raise AssertionError(f'Unexpected or mutating Redis command: {name}')


@pytest.fixture
def setup(tmp_path, monkeypatch):
    config = authority(tmp_path)
    fake = GenerationRedis(config)
    _library(monkeypatch, lambda *args, **kwargs: fake)
    return config, fake


def test_all_reads_select_native_generation_and_never_write(setup):
    config, fake = setup
    for operation, arguments in [('status', {}), ('digest', {}), ('node', {'id': 'aurora'}),
                                 ('node', {'id': 'file:personal:note'}), ('related', {'id': 'aurora'}),
                                 ('search', {'query': 'aurora'})]:
        packet = memory_redis.read(config, operation, arguments)
        assert packet['status'] == 'ok'
        assert packet['authority']['generation'] == fake.manifest['generation']
        assert packet['authority']['index'] == fake.index
        assert packet['authority']['hydrated_at'] == fake.manifest['hydrated_at']
        assert all('text' not in item for item in packet['items'])
        assert all(item.get('id') != 'foreign' for item in packet['items'])
    assert {call[0] for call in fake.calls} <= {'PING', 'GET', 'HGETALL', 'SCARD', 'FT.INFO', 'FT.SEARCH', 'FUNCTION', 'FCALL_RO'}
    assert all(call[1:3] == ('LIST', 'LIBRARYNAME') for call in fake.calls if call[0] == 'FUNCTION')


def test_serve_uses_generation_membership_and_current_wrong_verdict(setup):
    config, fake = setup
    text, reason = memory_redis.serve(config)
    assert reason is None and 'aurora' in text and 'retired' not in text
    text, reason = memory_redis.serve(config, prompt='aurora')
    assert reason is None and 'file:personal:note' in text
    assert 'POINTER BODY' not in text
    personal = Path(next(root['path'] for root in config['roots'] if root['id'] == 'personal'))
    (personal / '.verdicts.jsonl').write_text(json.dumps(dict(stem='note', verdict='wrong', digest='fixture',
                                                          who='local-user', at='2026-10-24')) + '\n', encoding='utf-8')
    text, reason = memory_redis.serve(config, prompt='aurora')
    assert reason is None and 'file:personal:note' not in text


@pytest.mark.parametrize('field,value', [('num_docs', 4), ('indexing', 1), ('hash_indexing_failures', 1),
                                        ('attributes', []), ('index_definition', ['key_type', 'HASH', 'prefixes', ['attune:memory:']])])
def test_incomplete_or_foreign_index_never_falls_back(setup, field, value):
    config, fake = setup
    fake.info[field] = value
    text, reason = memory_redis.serve(config)
    assert text is None and 'incomplete or incompatible' in reason
    assert not any(call[0] == 'FCALL_RO' for call in fake.calls)


@pytest.mark.parametrize('broken', ['active', 'marker', 'binding', 'bundle'])
def test_missing_foreign_or_incompatible_generation_is_unavailable(setup, broken):
    config, fake = setup
    if broken == 'active':
        fake.strings.pop(fake.active)
    elif broken == 'marker':
        fake.strings.pop(fake.prefix + 'manifest')
    elif broken == 'binding':
        fake.strings[fake.active] = canonical({**fake.manifest, 'binding': '0' * 64})
    else:
        fake.bundle += '\n-- unexpected replacement'
    text, reason = memory_redis.serve(config)
    assert text is None and reason
    assert not any(call[0] == 'FCALL_RO' for call in fake.calls)


def test_switch_after_query_or_during_filter_cannot_emit_old_context(setup):
    config, fake = setup
    fake.switch_on_node = True
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match='generation changed'):
        memory_redis.read(config, 'node', {'id': 'aurora'})
    fake.switch_on_node = False
    fake.strings[fake.active] = canonical(fake.manifest)
    fake.switch_on_membership = True
    text, reason = memory_redis.serve(config)
    assert text is None and 'generation changed' in reason


def test_native_server_errors_do_not_echo_credentials_or_indexed_text(setup, monkeypatch):
    config, fake = setup
    def fail(*args):
        raise FakeError('password=DO_NOT_PRINT indexed body=PRIVATE')
    monkeypatch.setattr(fake, 'execute_command', fail)
    text, reason = memory_redis.serve(config)
    assert text is None and 'unavailable' in reason
    assert 'DO_NOT_PRINT' not in reason and 'PRIVATE' not in reason


def test_no_root_authority_is_not_inferred_from_native_redis(setup):
    config, fake = setup
    text, reason = memory_redis.serve({'redis': config['redis']})
    assert text is None and reason
    assert not fake.calls


def test_native_connection_is_dedicated_and_expired_reads_issue_no_command(setup, monkeypatch):
    config, fake = setup
    options = {}
    def factory(*args, **kwargs):
        options.update(kwargs)
        return fake
    _library(monkeypatch, factory)
    memory = memory_redis.connect(memory_redis._configured(config))
    assert options['single_connection_client'] is True
    assert options['lib_name'] is None and options['lib_version'] is None
    memory.deadline = time.monotonic() - 1
    calls = list(fake.calls)
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match='deadline'):
        memory.node('aurora')
    assert fake.calls == calls


def test_socket_timeout_is_clamped_to_the_remaining_operation_budget(setup):
    config, fake = setup
    memory = memory_redis.connect(memory_redis._configured(config))
    class Socket:
        def settimeout(self, timeout):
            self.timeout = timeout
    class Connection:
        _sock = Socket()
    fake.connection = Connection()
    memory.deadline = time.monotonic() + .5
    memory.node('aurora')
    assert 0 < fake.connection._sock.timeout <= .5
    assert fake.connection.socket_timeout <= .5
    assert fake.connection.socket_connect_timeout <= .5


def test_malformed_function_payload_does_not_echo_raw_data(setup, monkeypatch):
    config, fake = setup
    original = fake.execute_command
    def malformed(name, *args):
        if name == 'FCALL_RO':
            return ['{"PRIVATE_DUPLICATE":1,"PRIVATE_DUPLICATE":2}']
        return original(name, *args)
    monkeypatch.setattr(fake, 'execute_command', malformed)
    text, reason = memory_redis.serve(config)
    assert text is None and 'malformed digest' in reason
    assert 'PRIVATE_DUPLICATE' not in reason


@pytest.mark.parametrize('operation,arguments', [('node', {'id': 'aurora'}), ('search', {'query': 'aurora'})])
def test_oversized_whole_reply_is_refused_without_truncation(setup, operation, arguments):
    config, fake = setup
    original = 'x' * (memory_redis.REPLY_LIMIT + 1)
    fake.hashes[fake.prefix + 'node:aurora']['description'] = original
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match='1 MiB packet bound'):
        memory_redis.read(config, operation, arguments)
    assert fake.hashes[fake.prefix + 'node:aurora']['description'] == original


def test_malformed_url_never_discloses_its_embedded_password(setup):
    config, fake = setup
    config['redis']['url'] = 'redis://user:PRIVATE_PASSWORD@\u2100host/0'
    text, reason = memory_redis.serve(config)
    assert text is None and 'endpoint is invalid' in reason
    assert 'PRIVATE_PASSWORD' not in reason and not fake.calls


def test_index_alias_cannot_replace_its_source_identifier(setup):
    config, fake = setup
    fake.info['attributes'][0][1] = 'unrelated_field'
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match='incomplete or incompatible'):
        memory_redis.read(config, 'node', {'id': 'aurora'})


@pytest.mark.parametrize('reply_source', ['search', 'active_count'])
def test_status_parser_errors_never_echo_malformed_reply_contents(setup, monkeypatch, reply_source):
    config, fake = setup
    original = fake.execute_command
    def malformed(name, *args):
        if name == 'FT.SEARCH' and reply_source == 'search':
            return ['PRIVATE_INDEXED_TEXT']
        return original(name, *args)
    monkeypatch.setattr(fake, 'execute_command', malformed)
    if reply_source == 'active_count':
        monkeypatch.setattr(fake, 'scard', lambda *args: 'PRIVATE_INDEXED_TEXT')
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match='malformed status reply') as error:
        memory_redis.read(config, 'status', {})
    assert 'PRIVATE_INDEXED_TEXT' not in str(error.value)


@pytest.mark.parametrize('query', ['socket_timeout=60&socket_connect_timeout=60',
    'decode_responses=false', 'retry_on_timeout=true', 'protocol=3', 'db=0&db=1'])
def test_native_url_options_cannot_override_reader_controls_before_connect(setup, monkeypatch, query):
    config, fake = setup
    config['redis']['url'] += '?' + query
    called = []
    _library(monkeypatch, lambda *args, **kwargs: called.append(True))
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match='db query parameter'):
        memory_redis.connect(memory_redis._configured(config))
    assert called == [] and fake.calls == []


def test_safe_database_query_keeps_initial_timeouts_bounded(setup, monkeypatch):
    import redis
    config, _ = setup
    config['redis']['url'] += '?db=0'
    observed = {}
    class OfflineConnection(redis.connection.Connection):
        def connect(self):
            observed.update(socket_timeout=self.socket_timeout, socket_connect_timeout=self.socket_connect_timeout)
            raise redis.exceptions.ConnectionError('offline probe; no network opened')
    monkeypatch.setattr(memory_redis, 'require_feature', lambda *args: redis)
    def factory(url, **kwargs):
        return redis.Redis.from_url(url, connection_class=OfflineConnection, **kwargs)
    with pytest.raises(memory_redis.MemoryRedisUnavailable, match='connection unavailable'):
        memory_redis.connect(memory_redis._configured(config), client_factory=factory)
    assert 0 < observed['socket_timeout'] <= 1
    assert 0 < observed['socket_connect_timeout'] <= 1


@pytest.mark.parametrize('selection', [
    {'projection': 'unknown', 'dataset': 'demo'}, {'projection': 'harness-v1'},
    {'dataset': 'demo'}, {'projection': 'harness-v1', 'dataset': 'demo', 'index': 'idx:legacy'},
    {'projection': 'harness-v1', 'dataset': 'foreign:dataset'},
])
def test_native_selection_is_explicit_and_cannot_override_cache_names(selection):
    with pytest.raises(ValueError):
        memory_redis.validate_config({'url': 'redis://fixture/0', **selection})
