"""Offline replay of actual normalized Voyage stages; no real key or network."""
# qualify: platform
# ruff: noqa: F811 -- imported pytest fixtures are injected by name.

import base64
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import struct
import zipfile

import pytest
import requests
import test_voyage_index_plugin as index_fixtures

from attune_harness import plugin_runtime
from attune_harness.extensions import discover
from attune_harness.review_contract import digest
from attune_harness.review_store import read_record
from attune_harness.voyage_provider import (PaidStageInterrupted, PaidStageUnresolved,
                                            StageJournal, embeddings, ranking)
from attune_harness.voyage_sources import PROFILE
from test_plugin_signing import base_signer, signers, signer  # noqa: F401
from test_voyage import corpus  # noqa: F401
from test_voyage_index_plugin import signed_index  # noqa: F401

FIXTURE = Path(__file__).parent / 'fixtures/voyage-live-recorded/stages.json.gz'
RETAINED_ARTIFACT = 'a950e357c5e145cc4c988fa043792def1ddd8a4dab90ec41c3fc6f83853db391'
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/voyage_plugin_differential.py'
spec = importlib.util.spec_from_file_location('voyage_plugin_differential', SCRIPT)
differential = importlib.util.module_from_spec(spec)
spec.loader.exec_module(differential)


def canonical_bundle_text(bundle):
    """Match the retained signed bundle's LF bytes on every host OS."""
    for name in ('manifest.json', 'SKILL.md'):
        path = bundle / name
        path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
    rewrite_code_newlines(bundle, lambda data: data.replace(b'\r\n', b'\n'))


def rewrite_code_newlines(bundle, convert):
    archive = bundle / 'code.zip'
    with zipfile.ZipFile(archive) as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    assert all(info.filename.endswith('.py') for info, _ in entries)
    if all(convert(data) == data for _, data in entries):
        return
    replacement = bundle / 'normalized-code.zip'
    with zipfile.ZipFile(replacement, 'w') as target:
        for info, data in entries:
            target.writestr(info, convert(data))
    replacement.replace(archive)


@pytest.fixture(autouse=True)
def signed_fixture_lf(monkeypatch):
    original = index_fixtures.build_bundle

    def build_with_lf(bundle):
        original(bundle)
        canonical_bundle_text(bundle)
        return discover(bundle / 'manifest.json')['artifact_digest']

    monkeypatch.setattr(index_fixtures, 'build_bundle', build_with_lf)


def test_signed_fixture_recovers_retained_artifact_after_crlf(tmp_path):
    from attune_voyage_plugin.bundle import build

    bundle = tmp_path / 'bundle'
    build(bundle)
    canonical_bundle_text(bundle)
    expected = {name: (bundle / name).read_bytes() for name in ('manifest.json', 'SKILL.md')}
    code = (bundle / 'code.zip').read_bytes()
    assert hashlib.sha256(code).hexdigest() == recorded()['provenance']['bundle_code_sha256']
    assert discover(bundle / 'manifest.json')['artifact_digest'] == RETAINED_ARTIFACT
    for name, value in expected.items():
        assert b'\n' in value and b'\r' not in value
        (bundle / name).write_bytes(value.replace(b'\n', b'\r\n'))
    rewrite_code_newlines(bundle, lambda data: data.replace(b'\n', b'\r\n'))
    assert discover(bundle / 'manifest.json')['artifact_digest'] != RETAINED_ARTIFACT
    canonical_bundle_text(bundle)
    assert {name: (bundle / name).read_bytes() for name in expected} == expected
    assert (bundle / 'code.zip').read_bytes() == code
    assert discover(bundle / 'manifest.json')['artifact_digest'] == RETAINED_ARTIFACT


def recorded():
    with gzip.open(FIXTURE, 'rt', encoding='utf-8') as stream:
        fixture = json.load(stream)
    assert fixture['kind'] == 'voyage-live-recorded-normalized-stages'
    assert fixture['schema_version'] == 1 and len(fixture['stages']) == 4
    for stage in fixture['stages']:
        assert digest({'kind': stage['kind'], 'request': stage['request'], 'profile': PROFILE}) == stage['stage_id']
        raw = json.dumps(stage['result'], sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                         allow_nan=False).encode()
        assert hashlib.sha256(raw).hexdigest() == stage['result_sha256']
    return fixture


def envelope(stage):
    result = stage['result']
    if stage['kind'] == 'embed':
        rows = [{'index': i, 'embedding': base64.b64encode(struct.pack('<1024f', *vector)).decode()}
                for i, vector in enumerate(result['vectors'])]
    else:
        rows = [{'index': row['index'], 'relevance_score': row['score']}
                for row in result['ranking']]
    return {'data': rows, 'usage': {'total_tokens': result['total_tokens']}}


def checked_payload(stage, method, url, kwargs):
    assert method == 'post'
    payload = json.loads(kwargs['data'])
    args = stage['request']
    if stage['kind'] == 'embed':
        assert url == 'https://api.voyageai.com/v1/embeddings'
        assert payload == {'input': args['texts'], 'input_type': args['input_type'],
                           'model': 'voyage-code-4', 'truncation': False,
                           'output_dimension': 1024, 'output_dtype': 'float',
                           'encoding_format': 'base64'}
    else:
        assert url == 'https://api.voyageai.com/v1/rerank'
        assert payload == {'query': args['query'], 'documents': args['documents'],
                           'model': 'rerank-2.5', 'top_k': args['k'], 'truncation': False}
    return envelope(stage)


def fake_response(value, url):
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(value, allow_nan=False).encode()
    response._content_consumed = True
    response.headers['Content-Type'] = 'application/json'
    response.url = url
    return response


def child_injection():
    """Patch only test bootstrap transport; signed production archive is unchanged."""
    return '''import base64, gzip, json, requests, socket, struct
with gzip.open(%r, 'rt', encoding='utf-8') as stream:
    _recorded = json.load(stream)['stages']
with open(config['request'], encoding='utf-8') as stream:
    _arguments = json.load(stream)['arguments']
_matches = [row for row in _recorded if row['request'] == _arguments]
if len(_matches) != 1:
    raise ValueError('Recorded request mismatch; no transport permitted')
_stage = _matches[0]
_calls = 0
def _fake_request(self, method, url, **kwargs):
    global _calls
    _calls += 1
    if _calls != 1 or method != 'post':
        raise ValueError('Recorded transport permits exactly one POST')
    _payload = json.loads(kwargs['data'])
    if _stage['kind'] == 'embed':
        _expected = {'input': _arguments['texts'], 'input_type': _arguments['input_type'],
                     'model': 'voyage-code-4', 'truncation': False,
                     'output_dimension': 1024, 'output_dtype': 'float',
                     'encoding_format': 'base64'}
        if url != 'https://api.voyageai.com/v1/embeddings' or _payload != _expected:
            raise ValueError('Recorded embedding wire request mismatch')
        _data = [{'index': i, 'embedding': base64.b64encode(struct.pack('<1024f', *v)).decode()}
                 for i, v in enumerate(_stage['result']['vectors'])]
    else:
        _expected = {'query': _arguments['query'], 'documents': _arguments['documents'],
                     'model': 'rerank-2.5', 'top_k': _arguments['k'], 'truncation': False}
        if url != 'https://api.voyageai.com/v1/rerank' or _payload != _expected:
            raise ValueError('Recorded rerank wire request mismatch')
        _data = [{'index': row['index'], 'relevance_score': row['score']}
                 for row in _stage['result']['ranking']]
    _response = requests.Response()
    _response.status_code = 200
    _response._content = json.dumps({'data': _data, 'usage':
        {'total_tokens': _stage['result']['total_tokens']}}, allow_nan=False).encode()
    _response._content_consumed = True
    _response.headers['Content-Type'] = 'application/json'
    _response.url = url
    return _response
requests.Session.request = _fake_request
def _no_socket(*args, **kwargs):
    raise AssertionError('Offline recorded test attempted a socket connection')
socket.socket.connect = _no_socket
socket.socket.connect_ex = _no_socket
''' % str(FIXTURE)


def validator(stage):
    if stage['kind'] == 'embed':
        return lambda value: embeddings(value, len(stage['request']['texts']))
    return lambda value: ranking(value, len(stage['request']['documents']), stage['request']['k'])


def test_recorded_stages_use_real_sdk_and_signed_bundle_without_network(signed_index, tmp_path, monkeypatch):
    fixture = recorded()
    selected, _, _, _ = signed_index(alter_paid=False)
    plain = copy.deepcopy(selected)
    plain.pop('voyage_plugin')
    # This fixture's enable resolves the actual installed distribution closure.
    # Its repeated pre/post-checks reuse that immutable accepted closure.
    assert fixture['provenance']['bundle_code_sha256'] == hashlib.sha256(
        (tmp_path / 'bundle/code.zip').read_bytes()).hexdigest()
    original_bootstrap = plugin_runtime.BOOTSTRAP
    assert "runpy.run_module(config['entry'], run_name='__main__')" in original_bootstrap
    monkeypatch.setattr(plugin_runtime, 'BOOTSTRAP', original_bootstrap.replace(
        "runpy.run_module(config['entry'], run_name='__main__')",
        child_injection() + "\nrunpy.run_module(config['entry'], run_name='__main__')"))
    def no_socket(*args, **kwargs):
        raise AssertionError('Offline recorded test attempted a socket connection')
    monkeypatch.setattr(socket.socket, 'connect', no_socket)
    monkeypatch.setattr(socket.socket, 'connect_ex', no_socket)

    for number, stage in enumerate(fixture['stages']):
        calls = []
        def fake_request(self, method, url, **kwargs):
            calls.append((method, url))
            assert len(calls) == 1
            return fake_response(checked_payload(stage, method, url, kwargs), url)
        monkeypatch.setattr(requests.Session, 'request', fake_request)
        left, right = tmp_path / f'plain-{number}', tmp_path / f'selected-{number}'
        request, kind, validate = stage['request'], stage['kind'], validator(stage)
        actual_left, receipt_left = StageJournal(left, plain, allow_provider=True).perform(
            kind, request, validate)
        actual_right, receipt_right = StageJournal(right, selected, allow_provider=True).perform(
            kind, request, validate)
        assert len(calls) == 1 and actual_left == actual_right == stage['result']
        assert receipt_left['stage_id'] == receipt_right['stage_id'] == stage['stage_id']
        assert receipt_left['new_tokens'] == receipt_right['new_tokens'] == stage['total_tokens']
        assert receipt_left['new_cost_usd'] == receipt_right['new_cost_usd'] == stage['cost_usd']
        assert receipt_right['plugin']['artifact_digest'] == fixture['provenance']['bundle_artifact_digest']
        compared = differential.compare(left, right, identical_responses=True)
        assert compared['inprocess'] == compared['selected']

        with monkeypatch.context() as replay_patch:
            replay_patch.delenv('VOYAGE_API_KEY')
            replay_patch.setattr(plugin_runtime, 'run_voyage_paid',
                                 lambda *a, **kw: pytest.fail('Completed replay launched a signed child'))
            for directory, cfg in ((left, plain), (right, selected)):
                result, replay = StageJournal(directory, cfg).perform(kind, request, validate)
                assert result == stage['result'] and replay['replayed'] is True
                assert replay['new_tokens'] == replay['new_cost_usd'] == 0


def test_recorded_request_mismatch_refuses_without_network(signed_index, tmp_path, monkeypatch):
    stage = recorded()['stages'][0]
    selected, _, _, _ = signed_index(alter_paid=False)
    monkeypatch.setattr(plugin_runtime, 'BOOTSTRAP', plugin_runtime.BOOTSTRAP.replace(
        "runpy.run_module(config['entry'], run_name='__main__')",
        child_injection() + "\nrunpy.run_module(config['entry'], run_name='__main__')"))
    changed = copy.deepcopy(stage['request'])
    changed['texts'][0] += ' modified'
    with pytest.raises(PaidStageUnresolved):
        StageJournal(tmp_path / 'mismatch', selected, allow_provider=True).perform(
            'embed', changed, lambda value: embeddings(value, len(changed['texts'])))
    ledger = read_record(tmp_path / 'mismatch')
    assert read_record(tmp_path / 'mismatch' / ledger['stages'][0])['status'] == 'unresolved'


def test_recorded_request_kill_retains_dispatching_without_redispatch(signed_index, tmp_path,
                                                                       monkeypatch):
    stage = recorded()['stages'][2]  # Actual captured query request; interruption is synthetic.
    from attune_voyage_plugin.bundle import GRANTS
    selected, _, _, _ = signed_index(alter_paid=False, grant={**GRANTS, 'time': 15})
    selected['max_provider_calls'] = 1
    plain = copy.deepcopy(selected)
    plain.pop('voyage_plugin')
    marker = tmp_path / 'entered-recorded-transport'
    recorded_request = json.dumps(stage['request'], sort_keys=True)
    injection = '''import json, os, pathlib, requests, socket, time
with open(config['request'], encoding='utf-8') as stream:
    _arguments = json.load(stream)['arguments']
if _arguments != json.loads(%r):
    raise ValueError('Recorded kill request differs before transport')
def _fake_request(self, method, url, **kwargs):
    _payload = json.loads(kwargs['data'])
    if (method != 'post' or url != 'https://api.voyageai.com/v1/embeddings' or
            _payload != {'input': _arguments['texts'], 'input_type': 'query',
                         'model': 'voyage-code-4', 'truncation': False,
                         'output_dimension': 1024, 'output_dtype': 'float',
                         'encoding_format': 'base64'}):
        raise ValueError('Recorded kill wire request differs')
    _fd = os.open(%r, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(_fd, 'w') as _stream:
        _stream.write('entered')
        _stream.flush()
        os.fsync(_stream.fileno())
    time.sleep(60)
    raise AssertionError('Timeout did not interrupt recorded fake transport')
requests.Session.request = _fake_request
def _no_socket(*args, **kwargs):
    raise AssertionError('Recorded kill test attempted a socket connection')
socket.socket.connect = _no_socket
socket.socket.connect_ex = _no_socket
''' % (recorded_request, str(marker))
    monkeypatch.setattr(plugin_runtime, 'BOOTSTRAP', plugin_runtime.BOOTSTRAP.replace(
        "runpy.run_module(config['entry'], run_name='__main__')",
        injection + "\nrunpy.run_module(config['entry'], run_name='__main__')"))
    class Interrupted:
        calls = 0
        def embed(self, *args):
            self.calls += 1
            raise PaidStageInterrupted('synthetic interrupted transport')
    provider = Interrupted()
    left, right = tmp_path / 'plain', tmp_path / 'selected'
    for directory, cfg, injected in ((left, plain, provider), (right, selected, None)):
        with pytest.raises(PaidStageUnresolved):
            StageJournal(directory, cfg, allow_provider=True, provider=injected).perform(
                'embed', stage['request'], validator(stage))
    assert marker.read_text() == 'entered'
    assert differential.compare(left, right, identical_responses=True)['selected'][0]['status'] == 'dispatching'
    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid',
                        lambda *a, **kw: pytest.fail('Uncertain replay launched a child'))
    for allow in (False, True):
        for directory, cfg, injected in ((left, plain, provider), (right, selected, None)):
            with pytest.raises(PaidStageUnresolved, match='No automatic retry'):
                StageJournal(directory, cfg, allow_provider=allow, provider=injected).perform(
                    'embed', stage['request'], validator(stage))
    assert provider.calls == 1
