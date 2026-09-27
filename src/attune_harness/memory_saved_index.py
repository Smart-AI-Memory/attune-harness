"""Optional, rebuildable Redis projection of authoritative saved records."""

import hashlib
import json
import os
import re
from urllib.parse import urlsplit


class RedisSavedIndex:
    """Lazy Redis adapter with a dedicated keyspace and bounded network waits.

    No connection is attempted at configuration time. The store treats every
    adapter failure as pending index work; credentials never enter a record.
    """

    def __init__(self, config):
        if not isinstance(config, dict) or set(config) != {'url_env', 'namespace'}:
            raise ValueError('Saved Redis config requires url_env and namespace')
        env, namespace = config['url_env'], config['namespace']
        if not isinstance(env, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', env):
            raise ValueError('Invalid saved Redis environment variable name')
        if not isinstance(namespace, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', namespace):
            raise ValueError('Invalid saved Redis namespace')
        self.url_env = env
        self.prefix = 'attune:harness:saved:v1:' + namespace + ':'
        self._client = None

    def _connection(self):
        if self._client is None:
            url = os.environ.get(self.url_env)
            if not url:
                raise RuntimeError('Saved index configuration is unavailable')
            try:
                # redis-py URL query options override keyword timeout bounds.
                if urlsplit(url).query:
                    raise ValueError('Saved index URLs cannot contain query options')
                from redis import Redis
                self._client = Redis.from_url(
                    url, socket_connect_timeout=1.0, socket_timeout=1.0,
                    retry_on_timeout=False, decode_responses=True,
                )
            except Exception:
                raise RuntimeError('Saved index connection is unavailable') from None
        return self._client

    def _key(self, record_id, scope):
        canonical = json.dumps(scope, sort_keys=True, separators=(',', ':'), allow_nan=False)
        scope_key = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        id_key = hashlib.sha256(record_id.encode('utf-8')).hexdigest()
        return self.prefix + scope_key + ':' + id_key

    def upsert(self, record):
        try:
            payload = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)
            self._connection().set(self._key(record['id'], record['scope']), payload)
        except Exception:
            raise RuntimeError('Saved index update is pending') from None

    def remove(self, record_id, scope):
        try:
            self._connection().delete(self._key(record_id, scope))
        except Exception:
            raise RuntimeError('Saved index removal is pending') from None
