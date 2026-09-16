"""Explicit Voyage calls and durable paid-stage receipts; no implicit retries."""

import copy
import math
import os
import time
from contextlib import contextmanager
from pathlib import Path

from .features import FeatureUnavailable, require_feature
from .review_contract import canonical, digest
from .review_store import RunStore, read_record, PersistenceError
from .voyage_sources import PROFILE

VOYAGE_VERSION = '0.5.0'
LANCEDB_VERSION = '0.38.0'
RATES = {'date': '2026-09-15', 'currency': 'USD', 'embedding_per_million': 0.12,
         'rerank_per_million': 0.05, 'credits_included': False}


class PaidStageUnresolved(RuntimeError):
    """A dispatched provider operation has unknown effects; never retry automatically."""


def number(value):
    return type(value) in (float, int) and math.isfinite(value)


def embeddings(value, count):
    vectors = value.get('vectors')
    if not isinstance(vectors, list) or len(vectors) != count:
        raise ValueError('Provider returned an incorrect embedding count')
    for vector in vectors:
        if (not isinstance(vector, list) or len(vector) != PROFILE['dimensions'] or
                any(not number(v) for v in vector) or not any(v != 0 for v in vector)):
            raise ValueError('Provider returned invalid embedding dimensions/values')
    usage(value)
    return value


def ranking(value, count, k):
    rows = value.get('ranking')
    if not isinstance(rows, list) or len(rows) != min(count, k):
        raise ValueError('Provider returned an incorrect rerank count')
    seen = set()
    previous = math.inf
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'index', 'score'} or
                type(row['index']) is not int or not 0 <= row['index'] < count or
                row['index'] in seen or not number(row['score']) or row['score'] > previous):
            raise ValueError('Provider returned invalid rerank indices/scores')
        seen.add(row['index'])
        previous = row['score']
    usage(value)
    return value


def usage(value):
    tokens = value.get('total_tokens')
    if tokens is not None and (type(tokens) is not int or tokens < 0):
        raise ValueError('Provider returned invalid token usage')
    return tokens  # Missing billing data is unknown, never zero.


class VoyageProvider:
    def __init__(self):
        key = os.environ.get('VOYAGE_API_KEY')
        if not key or not key.strip():
            raise FeatureUnavailable('Set VOYAGE_API_KEY locally before provider dispatch')
        sdk = require_feature('voyageai', 'voyageai', VOYAGE_VERSION, 'voyage')
        self.sdk = sdk
        self.client = sdk.Client(api_key=key, max_retries=0, timeout=60,
                                 base_url='https://api.voyageai.com/v1')

    @contextmanager
    def transport(self):
        # Qualified SDK 0.5.0 keeps its requests session per thread. Its default
        # transport retries connections twice even when Client(max_retries=0).
        # Override only this thread during our call, then restore other SDK users.
        import requests
        from voyageai.api_resources import api_requestor
        class BoundedSession(requests.Session):
            def request(self, *args, **kwargs):
                kwargs.update(allow_redirects=False, stream=True)
                response = super().request(*args, **kwargs)
                try:
                    data = bytearray()
                    for chunk in response.iter_content(65536):
                        data.extend(chunk)
                        if len(data) > 8 * 1024 * 1024:
                            raise ValueError('Provider response exceeds 8 MiB')
                    response._content = bytes(data)
                    response._content_consumed = True
                finally:
                    response.close()
                if 300 <= response.status_code < 400:
                    raise ValueError('Provider redirects are unsupported')
                return response
        context = api_requestor._thread_context
        old = dict(context.__dict__)
        session = BoundedSession()
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))
        context.session, context.session_create_time = session, time.time()
        try:
            yield
        finally:
            session.close()
            context.__dict__.clear()
            context.__dict__.update(old)

    def embed(self, texts, input_type):
        # The high-level SDK drops response indices. Validate the raw indices
        # before associating a paid vector with its source passage.
        with self.transport():
            result = self.sdk.Embedding.create(input=texts, model=PROFILE['embedding_model'], input_type=input_type,
                      truncation=False, output_dtype='float', output_dimension=PROFILE['dimensions'], **self.client._params)
        rows = result['data']
        if (len(rows) != len(texts) or any(type(r.get('index')) is not int for r in rows) or
                sorted(r['index'] for r in rows) != list(range(len(texts)))):
            raise ValueError('Provider returned invalid embedding indices')
        return embeddings({'vectors': [r['embedding'] for r in sorted(rows, key=lambda r: r['index'])],
                           'total_tokens': result.get('usage', {}).get('total_tokens')}, len(texts))

    def rerank(self, query, documents, k):
        with self.transport():
            result = self.sdk.Reranking.create(query=query, documents=documents, model=PROFILE['rerank_model'],
                                               top_k=k, truncation=False, **self.client._params)
        return ranking({'ranking': [{'index': r['index'], 'score': r['relevance_score']} for r in result['data']],
                        'total_tokens': result.get('usage', {}).get('total_tokens')}, len(documents), k)


class StageJournal:
    """Caller holds its enclosing run/index writer lease. Results live in bounded sidecars."""

    def __init__(self, directory: Path, cfg, *, allow_provider=False, provider=None):
        self.directory, self.cfg = directory, cfg
        self.allow_provider, self.provider = allow_provider, provider
        self.failed = False
        if directory.is_symlink():
            raise ValueError('Stage directory cannot be a symlink')
        directory.mkdir(exist_ok=True)
        self.ledger_store = RunStore(directory, existing=True)
        if self.ledger_store.path.exists():
            self.ledger = read_record(directory)
            if self.ledger.get('config_digest') != digest(cfg):
                raise ValueError('Provider stage ledger configuration changed')
        else:
            # A missing ledger beside stage files must not reset the paid budget.
            if any(directory.iterdir()):
                raise PaidStageUnresolved('Provider stage ledger is missing; refusing to reset billing history')
            self.ledger = {'schema_version': 1, 'recovery': {'profile': 'voyage-stage-ledger-v1'},
                           'config_digest': digest(cfg), 'stages': []}
            self._save(self.ledger_store, self.ledger)
        for stage in self.ledger['stages']:
            if not (directory / stage / 'record.json').is_file():
                raise PaidStageUnresolved('A recorded provider stage is missing; billing history is incomplete')

    def perform(self, kind, request, validate, *, reserve_calls=0):
        """Keep capacity for follow-on stages under the caller's writer lease.

        Completed stages replay without consuming or reserving paid-call slots.
        """
        if self.failed:
            raise PersistenceError('Stage persistence failed; dispatch stopped')
        if type(reserve_calls) is not int or reserve_calls < 0:
            raise ValueError('Reserved provider calls must be a nonnegative integer')
        payload = canonical(request)
        if len(payload.encode('utf-8')) + 2048 > self.cfg['max_request_bytes']:
            raise ValueError('Provider request exceeds accepted byte limit')
        key = digest({'kind': kind, 'request': request, 'profile': PROFILE})
        directory = self.directory / key
        if key in self.ledger['stages']:
            record = read_record(directory)
            if record.get('request_digest') != key or record.get('kind') != kind:
                raise ValueError('Provider stage identity changed')
            if record['status'] == 'completed':
                validate(record['result'])
                return copy.deepcopy(record['result']), {**record['receipt'], 'replayed': True, 'new_tokens': 0, 'new_cost_usd': 0.0}
            if record['status'] != 'prepared':
                raise PaidStageUnresolved('Provider stage may have been billed; inspect its receipt. No automatic retry.')
            if len(self.ledger['stages']) + reserve_calls > self.cfg['max_provider_calls']:
                raise PermissionError('Accepted provider-call budget cannot cover required follow-on stages')
            store = RunStore(directory, existing=True)
        else:
            if not self.allow_provider:
                raise FeatureUnavailable('Voyage uploads and paid calls require --allow-provider')
            if len(self.ledger['stages']) + 1 + reserve_calls > self.cfg['max_provider_calls']:
                raise PermissionError('Accepted provider-call budget cannot cover required stages')
            if directory.exists():
                raise PaidStageUnresolved('Unregistered stage files require inspection before another attempt')
            store = RunStore(directory)
            record = {'schema_version': 1, 'recovery': {'profile': 'voyage-paid-stage-v1'},
                      'kind': kind, 'request_digest': key, 'status': 'prepared'}
            self._save(store, record)
            self.ledger['stages'].append(key)
            self._save(self.ledger_store, self.ledger)
            if os.name == 'posix':
                fd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        if not self.allow_provider:
            raise FeatureUnavailable('Voyage uploads and paid calls require --allow-provider')
        # Constructing a client must not move a missing credential into unknown billing.
        if self.provider is None:
            self.provider = VoyageProvider()
        record['status'] = 'dispatching'
        self._save(store, record)
        started = time.monotonic()
        try:
            if kind == 'embed':
                result = self.provider.embed(request['texts'], request['input_type'])
            else:
                result = self.provider.rerank(request['query'], request['documents'], request['k'])
            validate(result)
        except BaseException as exc:
            # SDK error strings may include source text or secrets. Persist only the class.
            record.update(status='unresolved', error={'type': type(exc).__name__,
                          'detail': 'Provider response unavailable or invalid; billing unknown'})
            self._save(store, record)
            raise PaidStageUnresolved(record['error']['detail']) from None
        tokens = usage(result)
        rate = RATES['embedding_per_million' if kind == 'embed' else 'rerank_per_million']
        cost = None if tokens is None else tokens * rate / 1_000_000
        receipt = {'stage_id': key, 'kind': kind, 'replayed': False,
                   'total_tokens': tokens, 'new_tokens': tokens, 'new_cost_usd': cost,
                   'usage_status': 'unknown' if tokens is None else 'provider_reported',
                   'rate_snapshot': RATES, 'elapsed_seconds': time.monotonic() - started}
        record.update(status='completed', result=result, receipt=receipt)
        self._save(store, record)
        return copy.deepcopy(result), copy.deepcopy(receipt)

    def _save(self, store, record):
        try:
            store.save(record)
        except PersistenceError:
            self.failed = True
            raise
