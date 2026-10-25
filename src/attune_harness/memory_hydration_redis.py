"""Read one immutable, explicitly selected native hydration generation.

This module never publishes, repairs, loads functions or writes Redis keys.
The legacy reader remains the default and retains its separate fixed keyspace.
"""

import hashlib
import time
from urllib.parse import parse_qsl, urlsplit

from .memory_hydration_contract import (
    LIBRARY, LAYERS, function_digest, generation_index, generation_prefix,
    namespace, validate_manifest,
)
from .memory_redis import REPLY_LIMIT, MemoryRedisUnavailable, RedisMemory, open_client, resolve_url
from .review_contract import canonical

READ_SECONDS = 5.0


def _mapping(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, (list, tuple)) and len(value) % 2 == 0:
        return dict(zip(value[::2], value[1::2]))
    raise ValueError('Malformed native Redis metadata')


def _attribute(entry, key, default=None):
    if isinstance(entry, dict):
        return entry.get(key, default)
    if isinstance(entry, (list, tuple)):
        for position in range(0, len(entry) - 1, 2):
            if entry[position] == key:
                return entry[position + 1]
    return default


def _connection_settings(settings):
    try:
        url = resolve_url(settings)
        query = parse_qsl(urlsplit(url).query, keep_blank_values=True, strict_parsing=True)
    except (ValueError, UnicodeError, MemoryRedisUnavailable) as error:
        raise MemoryRedisUnavailable('Native Redis memory endpoint is invalid or unavailable; check its configuration') from error
    # redis-py gives URL options precedence over constructor kwargs. Keep the
    # database selector, but do not let URLs replace decoding, TLS or timeout
    # controls belonging to this bounded reader.
    if query and (len(query) != 1 or query[0][0] != 'db'
                  or not query[0][1].isascii() or not query[0][1].isdigit()):
        raise MemoryRedisUnavailable('Native Redis memory URL supports only one optional db query parameter')
    normalized = {**settings, 'url': url}
    normalized.pop('url_env', None)
    return normalized


class GenerationMemory(RedisMemory):
    """A manifest-selected reader with one host binding and one operation budget."""

    def __init__(self, client, settings, host, *, errors=(), started=None):
        super().__init__(client, settings, host, errors=errors)
        self.deadline = (time.monotonic() if started is None else started) + READ_SECONDS
        self.active_key = namespace(settings['dataset']) + 'active'
        binding = settings.get('_authority_digest')
        if not isinstance(binding, str):
            raise MemoryRedisUnavailable('Native Redis memory requires explicit host root authority')
        self.raw_manifest = self._call('selecting generation', client.get, self.active_key)
        try:
            self.manifest = validate_manifest(self.raw_manifest, binding, function_digest())
        except (ValueError, TypeError, KeyError, RecursionError) as error:
            raise MemoryRedisUnavailable('Native Redis memory has no complete, compatible host-bound manifest') from error
        generation = self.manifest['generation']
        self.prefix = generation_prefix(settings['dataset'], generation)
        self.index = generation_index(settings['dataset'], generation)

    def _budget(self):
        if time.monotonic() >= self.deadline:
            raise MemoryRedisUnavailable('Native Redis memory read deadline exceeded')

    def _call(self, what, function, *args):
        self._budget()
        if what in ('recall_digest', 'recall_related'):
            native = 'harness_recall_digest_v1' if what == 'recall_digest' else 'harness_recall_related_v1'
            args = ('FCALL_RO', native, 0, self.prefix, *args[3:])
        try:
            # The pinned client owns a dedicated connection in native mode.
            # Clamp its existing socket and reconnect timeouts to this operation,
            # without changing a shared pool or the legacy reader's timeouts.
            connection = getattr(self.client, 'connection', None)
            if connection is not None:
                remaining = max(0.001, self.deadline - time.monotonic())
                connection.socket_timeout = remaining
                connection.socket_connect_timeout = min(1.0, remaining)
                sock = getattr(connection, '_sock', None)
                if sock is not None:
                    sock.settimeout(remaining)
            value = function(*args)
        except self.errors as error:
            # Server errors may include indexed text, paths or credentials.
            raise MemoryRedisUnavailable(f'Native Redis memory unavailable during {what}') from error
        self._budget()
        return value

    def hydrated_at(self):
        return self.manifest['hydrated_at']

    def _decode(self, what, text):
        try:
            return super()._decode(what, text)
        except MemoryRedisUnavailable as error:
            raise MemoryRedisUnavailable(f'Native Redis memory returned a malformed {what} record') from error

    def search(self, query, *, layer=None, k=10):
        try:
            return super().search(query, layer=layer, k=k)
        except MemoryRedisUnavailable as error:
            if str(error).startswith('Redis memory returned'):
                raise MemoryRedisUnavailable('Native Redis memory returned a malformed search reply') from error
            raise

    def status(self):
        try:
            return super().status()
        except MemoryRedisUnavailable as error:
            if str(error).startswith('Redis memory returned'):
                raise MemoryRedisUnavailable('Native Redis memory returned a malformed status reply') from error
            raise

    def _index_info(self):
        reply = self._call('checking generation index', self.client.execute_command, 'FT.INFO', self.index)
        try:
            info = _mapping(reply)
            definition = _mapping(info['index_definition'])
            expected = [self.prefix + family + ':' for family in ('node', 'file', 'lesson', 'rule')]
            if definition.get('key_type') != 'HASH' or definition.get('prefixes') != expected:
                raise ValueError('Foreign index prefixes')
            expected_types = {name: 'TEXT' for name in ('name', 'description', 'text', 'updated_at')}
            expected_types.update({name: 'TAG' for name in ('type', 'status', 'layer', 'corpus', 'tags')})
            attributes = info['attributes']
            if not isinstance(attributes, (list, tuple)) or len(attributes) != len(expected_types):
                raise ValueError('Foreign index schema')
            actual = {_attribute(entry, 'attribute'): _attribute(entry, 'type') for entry in attributes}
            if (actual != expected_types or any(_attribute(entry, 'identifier') != _attribute(entry, 'attribute')
                                                 for entry in attributes)):
                raise ValueError('Foreign index schema')
            name = next(entry for entry in attributes if _attribute(entry, 'attribute') == 'name')
            if float(_attribute(name, 'WEIGHT', 1)) != 2:
                raise ValueError('Foreign index ranking')
            for field in ('indexing', 'hash_indexing_failures'):
                if str(info[field]) != '0':
                    raise ValueError('Incomplete index')
            if str(info['num_docs']) != str(sum(self.manifest['counts'].values())):
                raise ValueError('Incomplete generation')
        except (ValueError, TypeError, KeyError, StopIteration, OverflowError) as error:
            raise MemoryRedisUnavailable('Native Redis memory index is incomplete or incompatible') from error

    def require_hydration(self):
        reply = self._call('checking native function bundle', self.client.execute_command,
                           'FUNCTION', 'LIST', 'LIBRARYNAME', LIBRARY, 'WITHCODE')
        try:
            if not isinstance(reply, (list, tuple)) or len(reply) != 1:
                raise ValueError('Missing bundle')
            bundle = _mapping(reply[0])
            source = bundle['library_code']
            if (bundle.get('library_name') != LIBRARY or not isinstance(source, str)
                    or hashlib.sha256(source.encode('utf-8')).hexdigest() != self.manifest['function_digest']):
                raise ValueError('Foreign bundle')
        except (ValueError, TypeError, KeyError) as error:
            raise MemoryRedisUnavailable('Native Redis memory function bundle is missing or incompatible') from error
        self.ensure_current()

    def ensure_current(self):
        marker = self._call('checking completed generation', self.client.get, self.prefix + 'manifest')
        if marker != self.raw_manifest:
            raise MemoryRedisUnavailable('Native Redis memory generation is incomplete')
        self._index_info()
        active = self._call('checking generation selection', self.client.get, self.active_key)
        if active != self.raw_manifest:
            raise MemoryRedisUnavailable('Native Redis memory generation changed; reissue the read')

    def _packet(self, operation, status, items, **extra):
        packet = super()._packet(operation, status, items, **extra)
        packet['authority'].update(projection='harness-v1', dataset=self.settings['dataset'],
                                   generation=self.manifest['generation'], binding=self.manifest['binding'],
                                   source_digest=self.manifest['source_digest'])
        try:
            size = len(canonical(packet).encode('utf-8'))
        except (ValueError, TypeError, RecursionError) as error:
            raise MemoryRedisUnavailable('Native Redis memory packet is malformed') from error
        if size > REPLY_LIMIT:
            raise MemoryRedisUnavailable('Native Redis memory reply exceeds the 1 MiB packet bound')
        self.ensure_current()
        return packet


def connect(settings, *, client_factory=None, timeout=2.0):
    started = time.monotonic()
    connection_settings = _connection_settings(settings)
    try:
        client, host, errors = open_client(connection_settings, client_factory=client_factory,
                                           timeout=min(timeout, 1.0), exclusive=True)
    except (MemoryRedisUnavailable, ValueError, TypeError) as error:
        raise MemoryRedisUnavailable('Native Redis memory connection unavailable; inspect the configured endpoint') from error
    memory = GenerationMemory(client, settings, host, errors=errors, started=started)
    memory.require_hydration()
    return memory
