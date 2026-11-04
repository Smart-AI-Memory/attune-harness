"""Offline controls for the plan worker and exchange. No real network/processes.

Draft against S3 2026-11-04. Adapt only to a documented, qualified SSE profile;
never add production endpoint, CA, or test-token overrides to make these pass.
"""
# qualify: platform

import copy
import hashlib
import io
import json
from types import SimpleNamespace

import pytest

from attune_harness import plan_worker as worker
from attune_harness import plan_exchange as exchange
from attune_harness.process import ProcessResult

MODEL = 'explicit-model'
TOKEN = 'inert-bearer'
ANSWER = '{"text":"hello"}'


def body():
    return {'model': MODEL, 'instructions': 'Return JSON.',
            'input': [{'role': 'user', 'content': 'accepted context'}],
            'store': False, 'stream': True}


def message(text=ANSWER, item_id='item-1'):
    return {'id': item_id, 'type': 'message', 'role': 'assistant',
            'status': 'completed', 'content': [{'type': 'output_text', 'text': text, 'annotations': []}]}


def lifecycle(text=ANSWER):
    msg = message(text)
    return [
        {'type': 'response.created', 'sequence_number': 0,
         'response': {'id': 'resp-1', 'status': 'in_progress', 'model': MODEL, 'output': []}},
        {'type': 'response.output_item.added', 'sequence_number': 1,
         'response_id': 'resp-1', 'output_index': 0,
         'item': {'id': 'item-1', 'type': 'message', 'role': 'assistant', 'status': 'in_progress', 'content': []}},
        {'type': 'response.content_part.added', 'sequence_number': 2, 'item_id': 'item-1',
         'output_index': 0, 'content_index': 0, 'part': {'type': 'output_text', 'text': '', 'annotations': []}},
        {'type': 'response.output_text.delta', 'sequence_number': 3, 'item_id': 'item-1',
         'output_index': 0, 'content_index': 0, 'delta': text},
        {'type': 'response.output_text.done', 'sequence_number': 4, 'item_id': 'item-1',
         'output_index': 0, 'content_index': 0, 'text': text},
        {'type': 'response.content_part.done', 'sequence_number': 5, 'item_id': 'item-1',
         'output_index': 0, 'content_index': 0, 'part': {'type': 'output_text', 'text': text, 'annotations': []}},
        {'type': 'response.output_item.done', 'sequence_number': 6,
         'response_id': 'resp-1', 'output_index': 0, 'item': copy.deepcopy(msg)},
        {'type': 'response.completed', 'sequence_number': 7,
         'response': {'id': 'resp-1', 'status': 'completed', 'model': MODEL,
                      'error': None, 'incomplete_details': None, 'output': [msg]}},
    ]


def encode(events):
    return b''.join(('event: ' + ev['type'] + '\ndata: ' + json.dumps(ev, separators=(',', ':')) + '\n\n').encode() for ev in events) + b'data: [DONE]\n\n'


class FakeSocket:
    def __init__(self): self.timeouts = []
    def settimeout(self, value): self.timeouts.append(value)


class FakeResponse:
    def __init__(self, data=b'', status=200, content_type='text/event-stream'):
        self.source = io.BytesIO(data)
        self.status = status
        self.content_type = content_type
    def getheader(self, name, default=''):
        return self.content_type if name.lower() == 'content-type' else default
    def readline(self, n=-1): return self.source.readline(n)
    def read1(self, n=-1): return self.source.read1(n)
    def read(self, n=-1): return self.source.read(n)


class FakeHTTPS:
    def __init__(self, response):
        self.response, self.requests, self.connections = response, [], []
        self.sock = FakeSocket()
        self.closed = False
    def factory(self, host, port, **kwargs):
        self.connections.append((host, port, kwargs))
        return self
    def request(self, method, path, body, headers):
        self.requests.append((method, path, body, headers))
    def getresponse(self): return self.response
    def close(self): self.closed = True


@pytest.fixture
def transport(tmp_path, monkeypatch):
    ca = tmp_path / 'ca.pem'
    ca.write_bytes(b'inert CA bytes')
    context = object()
    contexts = []
    def context_factory(*, cafile=None, cadata=None):
        contexts.append((cafile, cadata))
        return context
    monkeypatch.setattr(worker.ssl, 'create_default_context', context_factory)
    value = {'body': body(), 'timeout': 10, 'ca_file': str(ca),
             'ca_sha256': hashlib.sha256(ca.read_bytes()).hexdigest()}
    return value, context, contexts


def run(transport, response):
    value, _, _ = transport
    fake = FakeHTTPS(response)
    result = worker.perform(value, TOKEN, connection_factory=fake.factory)
    return result, fake


def test_one_post_fixed_endpoint_body_tls_and_no_environment_influence(transport, monkeypatch):
    value, context, contexts = transport
    for key in ('HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'SSL_CERT_FILE', 'OPENAI_BASE_URL', 'OPENAI_API_KEY'):
        monkeypatch.setenv(key, 'https://inert.invalid/')
    result, fake = run(transport, FakeResponse(encode(lifecycle())))
    assert result['id'] == 'resp-1'
    assert len(fake.connections) == len(fake.requests) == 1
    host, port, options = fake.connections[0]
    assert (host, port) == ('api.openai.com', 443)
    assert options['context'] is context and options['timeout'] <= 10
    assert len(contexts) == 1
    cafile, cadata = contexts[0]
    assert cadata in (b'inert CA bytes', 'inert CA bytes') and cafile is None
    method, path, raw, headers = fake.requests[0]
    assert (method, path) == ('POST', '/v1/responses')
    assert json.loads(raw) == body()
    assert headers == {'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json',
                       'Accept': 'text/event-stream', 'Accept-Encoding': 'identity'}
    assert fake.closed


@pytest.mark.parametrize('status', [301, 302, 307, 308, 401, 429, 500, 503])
def test_http_error_never_redirects_or_retries(transport, status):
    fake = FakeHTTPS(FakeResponse(status=status))
    with pytest.raises(Exception): worker.perform(transport[0], TOKEN, connection_factory=fake.factory)
    assert len(fake.connections) == len(fake.requests) == 1
    assert fake.closed


@pytest.mark.parametrize('mutation', ['digest', 'missing_ca', 'symlink', 'body_extra', 'oversize', 'timeout', 'token'])
def test_refusal_before_network(transport, tmp_path, mutation):
    value = copy.deepcopy(transport[0])
    token = TOKEN
    if mutation == 'digest': value['ca_sha256'] = '0' * 64
    elif mutation == 'missing_ca': value['ca_file'] = str(tmp_path / 'missing')
    elif mutation == 'symlink':
        link = tmp_path / 'link'; link.symlink_to(value['ca_file']); value['ca_file'] = str(link)
    elif mutation == 'body_extra': value['body']['tools'] = []
    elif mutation == 'oversize': value['body']['input'][0]['content'] = 'x' * 1_048_577
    elif mutation == 'timeout': value['timeout'] = float('nan')
    elif mutation == 'token': token = 'bad\ntoken'
    fake = FakeHTTPS(FakeResponse())
    with pytest.raises(Exception): worker.perform(value, token, connection_factory=fake.factory)
    assert not fake.connections and not fake.requests


def test_non_sse_content_type_refuses_after_one_post(transport):
    fake = FakeHTTPS(FakeResponse(content_type='application/json'))
    with pytest.raises(Exception): worker.perform(transport[0], TOKEN, connection_factory=fake.factory)
    assert len(fake.requests) == 1


@pytest.mark.parametrize('mutation', [
    'missing_completion', 'duplicate_completion', 'failure', 'incomplete', 'wrong_model',
    'wrong_response_id', 'tool_item', 'tool_final', 'unannounced_final_item',
    'conflicting_delta', 'conflicting_item_done', 'partial_frame', 'error_event',
    'missing_created', 'reordered', 'wrong_item_id', 'repeated_sequence',
])
def test_invalid_or_conflicting_stream_fails_after_one_post(transport, mutation):
    events = lifecycle()
    if mutation == 'missing_completion': events.pop()
    elif mutation == 'duplicate_completion': events.append(copy.deepcopy(events[-1]))
    elif mutation == 'failure': events[-1]['response']['status'] = 'failed'
    elif mutation == 'incomplete': events[-1]['response']['incomplete_details'] = {'reason': 'limit'}
    elif mutation == 'wrong_model': events[-1]['response']['model'] = 'other'
    elif mutation == 'wrong_response_id': events[-1]['response']['id'] = 'other'
    elif mutation == 'tool_item': events[1]['item']['type'] = 'function_call'
    elif mutation == 'tool_final': events[-1]['response']['output'].append({'type': 'function_call'})
    elif mutation == 'unannounced_final_item': events[-1]['response']['output'][0]['id'] = 'other'
    elif mutation == 'conflicting_delta': events[3]['delta'] = '{"text":"other"}'
    elif mutation == 'conflicting_item_done': events[6]['item']['content'][0]['text'] = '{"text":"other"}'
    elif mutation == 'error_event': events.insert(-1, {'type': 'error', 'message': 'inert'})
    elif mutation == 'missing_created': events.pop(0)
    elif mutation == 'reordered': events[1], events[6] = events[6], events[1]
    elif mutation == 'wrong_item_id': events[3]['item_id'] = 'other'
    elif mutation == 'repeated_sequence': events[3]['sequence_number'] = 2
    data = encode(events)
    if mutation == 'partial_frame': data = data[:-2]
    fake = FakeHTTPS(FakeResponse(data))
    with pytest.raises(Exception): worker.perform(transport[0], TOKEN, connection_factory=fake.factory)
    assert len(fake.connections) == len(fake.requests) == 1


@pytest.mark.parametrize('bad', [
    b'data: {"type":"response.created","type":"response.completed"}\n\n',
    b'data: ' + b'[' * 34 + b'0' + b']' * 34 + b'\n\n',
    b'data: \xff\n\n',
    b'data: ' + b'x' * 262_145 + b'\n\n',
    b':x\n\n' * 350_000,
])
def test_malformed_or_over_limit_stream_fails_once(transport, bad):
    fake = FakeHTTPS(FakeResponse(bad))
    with pytest.raises(Exception): worker.perform(transport[0], TOKEN, connection_factory=fake.factory)
    assert len(fake.requests) == 1


def test_absolute_deadline_is_checked_during_trickling_stream(transport, monkeypatch):
    # No sleeping: each read advances the monotonic clock. A fresh socket idle
    # timeout alone permits an unlimited number of successful trickle reads.
    now = [0.0]
    monkeypatch.setattr(worker.time, 'monotonic', lambda: now[0])
    class Trickle(FakeResponse):
        def read1(self, n=-1):
            now[0] += 1
            return b':'
        def readline(self, n=-1):
            now[0] += 1
            return b':'
    fake = FakeHTTPS(Trickle())
    with pytest.raises((TimeoutError, ValueError)):
        worker.perform(transport[0], TOKEN, connection_factory=fake.factory)
    assert len(fake.requests) == 1
    assert now[0] <= 12
    assert fake.closed


@pytest.fixture
def exchange_case(monkeypatch, tmp_path):
    raw = json.dumps({'version': 1, 'request': 'accepted'})
    receipt = {'plan_wire_digest': hashlib.sha256(worker.wire(exchange.body(raw, MODEL))).hexdigest(),
               'dispatch_outcome': 'pending'}
    admission = SimpleNamespace(receipt=receipt, environment={})
    store = SimpleNamespace(current=lambda *_: True)
    context = {'effort': None, 'store': store, 'profile_id': 'opaque', 'generation': 1,
               'deadline': exchange.time.monotonic() + 60, 'ca_file': '/inert/ca', 'ca_sha256': '0' * 64}
    calls = {'claim': 0, 'release': 0, 'runner': []}
    monkeypatch.setattr(exchange.funding, 'check_issued', lambda *_: None)
    monkeypatch.setattr(exchange.funding, 'plan_context', lambda *_: context)
    def claim(*_):
        calls['claim'] += 1
        return {'ATTUNE_CHATGPT_ACCESS_TOKEN': TOKEN}
    monkeypatch.setattr(exchange.funding, 'claim', claim)
    def release(*_): calls['release'] += 1
    monkeypatch.setattr(exchange.funding, 'release', release)
    def runner(argv, prompt, **kwargs):
        calls['runner'].append((argv, prompt, kwargs))
        value = lifecycle()[-1]['response']
        return ProcessResult(argv, 0, json.dumps(value), '')
    obj = exchange.PlanExchange(model=MODEL, cwd=tmp_path, admission=admission, runner=runner)
    return obj, raw, receipt, context, calls


def test_exchange_uses_one_supervised_child_and_host_digest(exchange_case):
    obj, raw, receipt, _, calls = exchange_case
    result = json.loads(obj(raw))
    assert result == {'version': 1, 'request_digest': hashlib.sha256(raw.encode()).hexdigest(), 'text': 'hello'}
    assert calls['claim'] == calls['release'] == len(calls['runner']) == 1
    argv, prompt, options = calls['runner'][0]
    assert argv[1:3] == ('-I', '-S') and argv[-1].endswith('plan_worker.py')
    assert TOKEN not in prompt
    assert options['environment'] == {'ATTUNE_CHATGPT_ACCESS_TOKEN': TOKEN}
    assert receipt['dispatch_outcome'] == 'completed'


def test_exchange_mismatched_wire_has_zero_claim_or_child(exchange_case):
    obj, raw, receipt, _, calls = exchange_case
    receipt['plan_wire_digest'] = '0' * 64
    with pytest.raises(Exception): obj(raw)
    assert calls['claim'] == len(calls['runner']) == 0
    assert calls['release'] == 1


@pytest.mark.parametrize('failure,expected', [('launch_failed', 'not_started'),
    ('cancelled_before_start', 'not_started'), ('timeout_effects_unknown', 'unknown'),
    ('nonzero_exit', 'unknown')])
def test_exchange_process_failure_releases_and_preserves_effects(exchange_case, failure, expected):
    obj, raw, receipt, _, calls = exchange_case
    def runner(argv, prompt, **kwargs):
        calls['runner'].append((argv, prompt, kwargs))
        return ProcessResult(argv, None if failure != 'nonzero_exit' else 1, '', 'secret diagnostics', failure)
    obj.runner = runner
    with pytest.raises(Exception) as exc: obj(raw)
    assert TOKEN not in str(exc.value) and 'secret diagnostics' not in str(exc.value)
    assert calls['claim'] == calls['release'] == len(calls['runner']) == 1
    assert receipt['dispatch_outcome'] == expected


@pytest.mark.parametrize('change', ['tool', 'missing_message', 'bad_text', 'oversize', 'wrong_model'])
def test_exchange_invalid_final_never_retries(exchange_case, change):
    obj, raw, receipt, _, calls = exchange_case
    def runner(argv, prompt, **kwargs):
        calls['runner'].append((argv, prompt, kwargs))
        result = copy.deepcopy(lifecycle()[-1]['response'])
        if change == 'tool': result['output'].append({'type': 'function_call'})
        elif change == 'missing_message': result['output'] = []
        elif change == 'bad_text': result['output'][0]['content'][0]['text'] = '{bad json'
        elif change == 'oversize': result['output'][0]['content'][0]['text'] = json.dumps({'text': 'x' * 65537})
        elif change == 'wrong_model': result['model'] = 'different'
        return ProcessResult(argv, 0, json.dumps(result), '')
    obj.runner = runner
    with pytest.raises(Exception): obj(raw)
    assert calls['claim'] == calls['release'] == len(calls['runner']) == 1
    assert receipt['dispatch_outcome'] == 'unknown'

@pytest.mark.parametrize('mutation', ['index', 'content_part_conflict', 'content_part_order', 'created_status'])
def test_stream_event_schema_is_correlated(transport, mutation):
    events = lifecycle()
    if mutation == 'index': events[4]['output_index'] = 7
    elif mutation == 'content_part_conflict': events[5]['part']['text'] = '{"text":"different"}'
    elif mutation == 'content_part_order':
        events[2], events[5] = events[5], events[2]
        events[2]['sequence_number'], events[5]['sequence_number'] = 2, 5
    elif mutation == 'created_status': events[0]['response']['status'] = 'failed'
    fake = FakeHTTPS(FakeResponse(encode(events)))
    with pytest.raises(Exception): worker.perform(transport[0], TOKEN, connection_factory=fake.factory)
    assert len(fake.requests) == 1


def test_claimed_admission_is_released_if_claimed_environment_is_invalid(exchange_case, monkeypatch):
    obj, raw, _, _, calls = exchange_case
    def claim(*_):
        calls['claim'] += 1
        return {}
    monkeypatch.setattr(exchange.funding, 'claim', claim)
    with pytest.raises(Exception): obj(raw)
    assert calls['claim'] == calls['release'] == 1
    assert not calls['runner']


def test_invalidated_generation_is_refused_before_child_start(exchange_case):
    obj, raw, _, context, calls = exchange_case
    context['store'].current = lambda *_: False
    with pytest.raises(Exception): obj(raw)
    assert calls['release'] == 1 and not calls['runner']


def test_tls_context_uses_exact_hashed_ca_bytes(tmp_path, monkeypatch):
    ca = tmp_path / 'ca.pem'
    original = b'original trusted CA bytes'
    ca.write_bytes(original)
    value = {'body': body(), 'timeout': 10, 'ca_file': str(ca),
             'ca_sha256': hashlib.sha256(original).hexdigest()}
    observed = []
    def context_factory(*, cafile=None, cadata=None):
        # Simulate substitution exactly as context creation starts.
        ca.write_bytes(b'different CA bytes')
        observed.append(cadata if cadata is not None else open(cafile, 'rb').read())
        return object()
    monkeypatch.setattr(worker.ssl, 'create_default_context', context_factory)
    fake = FakeHTTPS(FakeResponse(encode(lifecycle())))
    worker.perform(value, TOKEN, connection_factory=fake.factory)
    loaded = observed[0]
    assert loaded == original or loaded == original.decode()
    assert len(fake.requests) == 1


@pytest.mark.parametrize('mutation', ['no_content_events', 'missing_content_done', 'text_before_content', 'item_before_content_done'])
def test_content_lifecycle_required_and_ordered(transport, mutation):
    events = lifecycle()
    if mutation == 'no_content_events': events = [ev for ev in events if not ev['type'].startswith('response.content_part.')]
    elif mutation == 'missing_content_done': events = [ev for ev in events if ev['type'] != 'response.content_part.done']
    elif mutation == 'text_before_content': events[2], events[3] = events[3], events[2]
    elif mutation == 'item_before_content_done': events[5], events[6] = events[6], events[5]
    for index, ev in enumerate(events): ev['sequence_number'] = index
    fake = FakeHTTPS(FakeResponse(encode(events)))
    with pytest.raises(Exception): worker.perform(transport[0], TOKEN, connection_factory=fake.factory)
    assert len(fake.requests) == 1


def test_real_tls_context_requires_certificate_and_hostname(tmp_path):
    import hashlib
    import ssl
    from pathlib import Path
    certifi = pytest.importorskip('certifi')
    ca = tmp_path / 'trusted.pem'
    ca.write_bytes(Path(certifi.where()).read_bytes())
    packet = {'body': body(), 'timeout': 2, 'ca_file': str(ca),
              'ca_sha256': hashlib.sha256(ca.read_bytes()).hexdigest()}
    fake = FakeHTTPS(FakeResponse(encode(lifecycle())))
    def factory(host, port, **kw):
        assert kw['context'].verify_mode == ssl.CERT_REQUIRED
        assert kw['context'].check_hostname is True
        return fake.factory(host, port, **kw)
    result = worker.perform(packet, TOKEN, connection_factory=factory)
    assert result['status'] == 'completed' and len(fake.requests) == 1


@pytest.mark.parametrize('bad_event', [
    {'type':'response.output_item.added'},
    {'type':'response.reasoning_text.delta','item_id':'item-1','output_index':0,'delta':'wrong type'},
    {'type':'response.in_progress','response':{'id':'resp-1','model':'explicit-model','status':'failed','error':{'code':'quota_exhausted'}}},
])
def test_malformed_event_refused_without_retry(transport,bad_event):
    events=lifecycle(); events.insert(3,bad_event)
    for i,e in enumerate(events): e['sequence_number']=i
    fake=FakeHTTPS(FakeResponse(encode(events)))
    with pytest.raises(ValueError): worker.perform(transport[0],TOKEN,connection_factory=fake.factory)
    assert len(fake.requests)==1
