"""The real worker request builder is exercised without opening a socket."""
# qualify: platform

import io
import json
import urllib.error
import urllib.request

import pytest

from attune_harness import openai_worker as worker


KEY = 'synthetic_worker_key_0123456789'


def setup(monkeypatch, *, response=b'{"fixture":true}', error=None):
    calls = []
    monkeypatch.setenv('OPENAI_API_KEY', KEY)
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://unqualified.invalid')
    monkeypatch.setenv('HTTPS_PROXY', 'https://unqualified-proxy.invalid')
    monkeypatch.setattr(worker.sys, 'stdin', io.StringIO(json.dumps({
        'body': {'model': 'fixture-model', 'store': False}, 'timeout': 5})))

    class Reply(io.BytesIO):
        def read(self, limit):
            assert limit == 1_048_577
            return super().read(limit)

    class Opener:
        def open(self, request, *, timeout):
            calls.append(request)
            assert request.full_url == 'https://api.openai.com/v1/responses'
            assert request.get_method() == 'POST' and timeout == 5
            assert request.get_header('Authorization') == 'Bearer ' + KEY
            assert json.loads(request.data) == {'model': 'fixture-model', 'store': False}
            if error is not None:
                raise error
            return Reply(response)

    def build(*handlers):
        assert len(handlers) == 2
        assert isinstance(handlers[0], urllib.request.ProxyHandler) and handlers[0].proxies == {}
        assert isinstance(handlers[1], worker.NoRedirect)
        assert handlers[1].redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid') is None
        return Opener()

    monkeypatch.setattr(worker.urllib.request, 'build_opener', build)
    return calls


def test_worker_uses_exact_endpoint_and_explicit_header_without_proxy_or_redirect(monkeypatch, capsys):
    calls = setup(monkeypatch)
    assert worker.main() == 0
    out = capsys.readouterr()
    assert out.out == '{"fixture":true}' and out.err == '' and len(calls) == 1


def test_worker_preserves_utf8_under_a_non_utf8_console_encoding(monkeypatch):
    raw = '{"text":"crème 日本語"}'.encode('utf-8')
    calls = setup(monkeypatch, response=raw)
    buffer = io.BytesIO()
    console = io.TextIOWrapper(buffer, encoding='ascii', write_through=True)
    monkeypatch.setattr(worker.sys, 'stdout', console)
    assert worker.main() == 0 and len(calls) == 1
    assert buffer.getvalue() == raw


@pytest.mark.parametrize('error', [RuntimeError(KEY), urllib.error.URLError(KEY),
    urllib.error.HTTPError('https://unqualified.invalid', 401, KEY, {'Account': KEY}, io.BytesIO(KEY.encode()))])
def test_worker_never_echoes_error_body_headers_or_key_and_never_retries(monkeypatch, capsys, error):
    calls = setup(monkeypatch, error=error)
    assert worker.main() == 2
    out = capsys.readouterr()
    assert out.out == '' and out.err in ('openai_http_error', 'openai_transport_error')
    assert KEY not in out.err and len(calls) == 1


def test_worker_refuses_oversized_response(monkeypatch, capsys):
    calls = setup(monkeypatch, response=b'x' * 1_048_577)
    assert worker.main() == 2 and len(calls) == 1
    out = capsys.readouterr()
    assert out.out == '' and out.err == 'openai_transport_error'


def test_worker_refuses_oversized_input_before_request(monkeypatch, capsys):
    calls = setup(monkeypatch)
    monkeypatch.setattr(worker.sys, 'stdin', io.StringIO('x' * 3_000_001))
    assert worker.main() == 2 and calls == []
    assert capsys.readouterr().err == 'openai_transport_error'
