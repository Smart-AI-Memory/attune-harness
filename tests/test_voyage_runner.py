"""Offline probes for the real signed-runner source; no Voyage network calls."""

from contextlib import nullcontext
import json
import sys
from types import SimpleNamespace

import pytest

from attune_voyage_plugin import provider


def test_real_embed_runner_serializes_full_32_vector_batch_within_accepted_bound(monkeypatch, tmp_path):
    from attune_harness.voyage_provider import embeddings
    from attune_voyage_plugin import common
    from attune_voyage_plugin.bundle import GRANTS

    vector = [0.12345678901234568] * 1024
    rows = [{'index': i, 'embedding': vector} for i in range(32)]
    monkeypatch.setattr(provider, 'client', lambda: SimpleNamespace(_params={'api_key': 'offline-fixture'}))
    monkeypatch.setattr(provider, 'transport', nullcontext)
    monkeypatch.setattr(provider, 'voyageai', SimpleNamespace(Embedding=SimpleNamespace(
        create=lambda **kwargs: {'data': rows, 'usage': {'total_tokens': 3200}})))
    value = provider.embed([f'text {i}' for i in range(32)], 'document')
    output = tmp_path / 'result.json'
    monkeypatch.setattr(sys, 'argv', ['embed', 'request.json', str(output)])
    common.result(value)
    assert 65536 < output.stat().st_size <= GRANTS['output']['result']
    assert embeddings(json.loads(output.read_text()), 32) == value


def test_real_runner_uses_fixed_sdk_profile_and_raw_embedding_indices(monkeypatch):
    seen = {}
    def create(**kwargs):
        seen.update(kwargs)
        return {'data': [{'index': 1, 'embedding': [2.0]}, {'index': 0, 'embedding': [1.0]}],
                'usage': {'total_tokens': 7}}
    monkeypatch.setattr(provider, 'client', lambda: SimpleNamespace(_params={'api_key': 'offline-fixture'}))
    monkeypatch.setattr(provider, 'transport', nullcontext)
    monkeypatch.setattr(provider, 'voyageai', SimpleNamespace(Embedding=SimpleNamespace(create=create)))
    assert provider.embed(['one', 'two'], 'document') == {'vectors': [[1.0], [2.0]], 'total_tokens': 7}
    assert seen == {'input': ['one', 'two'], 'model': 'voyage-code-4', 'input_type': 'document',
                    'truncation': False, 'output_dtype': 'float', 'output_dimension': 1024,
                    'api_key': 'offline-fixture'}
    def duplicate(**kwargs):
        return {'data': [{'index': 0, 'embedding': [1.0]}, {'index': 0, 'embedding': [2.0]}]}
    monkeypatch.setattr(provider.voyageai.Embedding, 'create', duplicate)
    with pytest.raises(ValueError, match='indices'):
        provider.embed(['one', 'two'], 'query')


def test_real_runner_rerank_indices_and_profile(monkeypatch):
    seen = {}
    def create(**kwargs):
        seen.update(kwargs)
        return {'data': [{'index': 1, 'relevance_score': 0.9}], 'usage': {'total_tokens': 11}}
    monkeypatch.setattr(provider, 'client', lambda: SimpleNamespace(_params={'api_key': 'offline-fixture'}))
    monkeypatch.setattr(provider, 'transport', nullcontext)
    monkeypatch.setattr(provider, 'voyageai', SimpleNamespace(Reranking=SimpleNamespace(create=create)))
    assert provider.rerank('q', ['a', 'b'], 1) == {'ranking': [{'index': 1, 'score': 0.9}], 'total_tokens': 11}
    assert seen == {'query': 'q', 'documents': ['a', 'b'], 'model': 'rerank-2.5',
                    'top_k': 1, 'truncation': False, 'api_key': 'offline-fixture'}
    def invalid(**kwargs):
        return {'data': [{'index': 3, 'relevance_score': 0.9}]}
    monkeypatch.setattr(provider.voyageai.Reranking, 'create', invalid)
    with pytest.raises(ValueError, match='indices'):
        provider.rerank('q', ['a', 'b'], 1)


def test_real_runner_transport_has_zero_retries_no_redirects_and_response_bound(monkeypatch):
    requests_seen = []
    class Response:
        def __init__(self, status=200, chunks=()):
            self.status_code, self.chunks, self.closed = status, chunks, False
        def iter_content(self, size):
            yield from self.chunks
        def close(self):
            self.closed = True
    response = Response(chunks=(b'bounded',))
    def request(self, *args, **kwargs):
        requests_seen.append((self, kwargs))
        return response
    monkeypatch.setattr(provider.requests.Session, 'request', request)
    context = provider.api_requestor._thread_context
    with provider.transport():
        session = context.session
        assert session.get_adapter('https://').max_retries.total == 0
        session.request('GET', 'https://example.invalid')
    assert requests_seen[0][1]['allow_redirects'] is False
    assert requests_seen[0][1]['stream'] is True and response.closed
    assert response._content == b'bounded'
    redirect = Response(status=302, chunks=(b'location',))
    monkeypatch.setattr(provider.requests.Session, 'request', lambda *a, **kw: redirect)
    with provider.transport():
        with pytest.raises(ValueError, match='redirects'):
            context.session.request('GET', 'https://example.invalid')
    assert redirect.closed
    oversized = Response(chunks=(b'x' * (8 * 1024 * 1024 + 1),))
    monkeypatch.setattr(provider.requests.Session, 'request', lambda *a, **kw: oversized)
    with provider.transport():
        with pytest.raises(ValueError, match='8 MiB'):
            context.session.request('GET', 'https://example.invalid')
    assert oversized.closed


def test_real_runner_client_bounds_without_dispatch(monkeypatch):
    seen = {}
    class Client:
        def __init__(self, **kwargs):
            seen.update(kwargs)
    monkeypatch.setenv('VOYAGE_API_KEY', 'offline-fixture-not-a-real-key')
    monkeypatch.setattr(provider, 'voyageai', SimpleNamespace(Client=Client))
    provider.client()
    assert seen == {'api_key': 'offline-fixture-not-a-real-key', 'max_retries': 0,
                    'timeout': 60, 'base_url': 'https://api.voyageai.com/v1'}
