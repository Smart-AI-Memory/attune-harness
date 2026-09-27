"""Bounded Voyage SDK calls; the host owns paid-stage authority and validation."""

import contextlib
import os
import time

import requests
import voyageai
from voyageai.api_resources import api_requestor

ENDPOINT = 'https://api.voyageai.com/v1'


@contextlib.contextmanager
def transport():
    class BoundedSession(requests.Session):
        def request(self, *args, **kwargs):
            kwargs.update(allow_redirects=False, stream=True)
            response = super().request(*args, **kwargs)
            try:
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > 8 * 1024 * 1024:
                        raise ValueError('Voyage response exceeds 8 MiB')
                response._content = bytes(data)
                response._content_consumed = True
            finally:
                response.close()
            if 300 <= response.status_code < 400:
                raise ValueError('Voyage redirects are unsupported')
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


def client():
    key = os.environ.get('VOYAGE_API_KEY')
    if not key or not key.strip():
        raise ValueError('VOYAGE_API_KEY is absent')
    return voyageai.Client(api_key=key, max_retries=0, timeout=60, base_url=ENDPOINT)


def embed(texts, input_type):
    if (not isinstance(texts, list) or not texts or any(not isinstance(text, str) for text in texts)
            or input_type not in ('document', 'query')):
        raise ValueError('Invalid Voyage embedding request')
    sdk_client = client()
    with transport():
        response = voyageai.Embedding.create(input=texts, model='voyage-code-4', input_type=input_type,
            truncation=False, output_dtype='float', output_dimension=1024, **sdk_client._params)
    rows = response['data']
    if (len(rows) != len(texts) or any(type(row.get('index')) is not int for row in rows)
            or sorted(row['index'] for row in rows) != list(range(len(texts)))):
        raise ValueError('Voyage returned invalid embedding indices')
    return {'vectors': [row['embedding'] for row in sorted(rows, key=lambda row: row['index'])],
            'total_tokens': response.get('usage', {}).get('total_tokens')}


def rerank(query, documents, k):
    if (not isinstance(query, str) or not isinstance(documents, list) or
            any(not isinstance(text, str) for text in documents) or
            type(k) is not int or not 1 <= k <= len(documents)):
        raise ValueError('Invalid Voyage rerank request')
    sdk_client = client()
    with transport():
        response = voyageai.Reranking.create(query=query, documents=documents, model='rerank-2.5',
                                              top_k=k, truncation=False, **sdk_client._params)
    rows = response['data']
    indices = [row.get('index') for row in rows]
    if (len(rows) != k or any(type(index) is not int for index in indices) or
            len(set(indices)) != len(indices) or any(not 0 <= index < len(documents) for index in indices)):
        raise ValueError('Voyage returned invalid rerank indices')
    return {'ranking': [{'index': row['index'], 'score': row['relevance_score']} for row in rows],
            'total_tokens': response.get('usage', {}).get('total_tokens')}
