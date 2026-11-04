"""Isolated one-POST plan worker. No SDK, auth discovery, retries or redirects."""

import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import ssl
import sys
import time

LIMIT = 1_048_576
FRAME = 262_144
EVENTS = {'response.created', 'response.in_progress', 'response.completed',
          'response.output_item.added', 'response.output_item.done',
          'response.content_part.added', 'response.content_part.done',
          'response.output_text.delta', 'response.output_text.done',
          'response.reasoning_summary_part.added', 'response.reasoning_summary_part.done',
          'response.reasoning_summary_text.delta', 'response.reasoning_summary_text.done',
          'response.reasoning_text.delta', 'response.reasoning_text.done'}


def unique(items):
    result = {}
    for key, value in items:
        if key in result: raise ValueError('duplicate field')
        result[key] = value
    return result


def bounded(value, depth=0):
    if depth > 32: raise ValueError('JSON depth')
    if isinstance(value, dict):
        for item in value.values(): bounded(item, depth + 1)
    elif isinstance(value, list):
        for item in value: bounded(item, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError('nonfinite JSON')
    return value


def loads(raw):
    return bounded(json.loads(raw, object_pairs_hook=unique))


def wire(body):
    required = {'model', 'instructions', 'input', 'store', 'stream'}
    if not isinstance(body, dict) or set(body) not in (required, required | {'reasoning'}):
        raise ValueError('wire fields')
    if body['store'] is not False or body['stream'] is not True:
        raise ValueError('wire policy')
    if not isinstance(body['model'], str) or not 1 <= len(body['model']) <= 200:
        raise ValueError('wire model')
    if not isinstance(body['instructions'], str) or not body['instructions']:
        raise ValueError('wire instructions')
    messages = body['input']
    if (not isinstance(messages, list) or len(messages) != 1
            or set(messages[0]) != {'role', 'content'} or messages[0]['role'] != 'user'
            or not isinstance(messages[0]['content'], str) or not messages[0]['content']):
        raise ValueError('wire context')
    if 'reasoning' in body and (set(body['reasoning']) != {'effort'}
            or body['reasoning']['effort'] not in ('none', 'minimal', 'low', 'medium', 'high', 'xhigh')):
        raise ValueError('wire effort')
    raw = json.dumps(body, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    if len(raw) > LIMIT: raise ValueError('wire limit')
    return raw


def stream_lines(response, connection, deadline):
    total, pending = 0, b''
    while True:
        seconds = deadline - time.monotonic()
        if seconds <= 0: raise TimeoutError('deadline')
        if connection.sock: connection.sock.settimeout(seconds)
        chunk = response.read1(16384)
        total += len(chunk)
        if total > LIMIT: raise ValueError('stream limit')
        if not chunk:
            if pending: raise ValueError('unterminated line')
            return
        pending += chunk
        while b'\n' in pending:
            line, pending = pending.split(b'\n', 1)
            if len(line) > FRAME: raise ValueError('frame limit')
            yield line + b'\n'
        if len(pending) > FRAME: raise ValueError('frame limit')


def read_stream(response, connection, deadline, model):
    size, previous = 0, -1
    frame, complete, identity = [], None, None
    added, done, deltas, text_done, positions, parts = {}, {}, {}, {}, {}, {}
    created = False
    for line in stream_lines(response, connection, deadline):
        size += len(line)
        if size > FRAME: raise ValueError('frame limit')
        if line not in (b'\n', b'\r\n'):
            frame.append(line.decode('utf-8')); continue
        data, event_name = [], None
        for field in frame:
            if field.startswith(':'): continue
            key, colon, value = field.rstrip('\r\n').partition(':')
            if not colon or key not in ('data', 'event', 'id'): raise ValueError('SSE field')
            if key == 'data': data.append(value.lstrip(' '))
            if key == 'event':
                if event_name is not None: raise ValueError('duplicate event')
                event_name = value.lstrip(' ')
        frame, size = [], 0
        if not data: continue
        if '\n'.join(data) == '[DONE]':
            if complete is None: raise ValueError('missing completion')
            continue
        value = loads('\n'.join(data))
        kind = value.get('type')
        if kind not in EVENTS or (event_name and event_name != kind): raise ValueError('event type')
        if complete is not None: raise ValueError('event after completion')
        sequence = value.get('sequence_number')
        if sequence is not None:
            if type(sequence) is not int or sequence <= previous: raise ValueError('event sequence')
            previous = sequence
        if not created and kind != 'response.created': raise ValueError('missing creation')
        result = value.get('response')
        if kind in ('response.created', 'response.in_progress'):
            if (not isinstance(result, dict) or result.get('status') != 'in_progress'
                    or result.get('error') is not None or result.get('incomplete_details') is not None):
                raise ValueError('invalid progress event')
        if kind in ('response.output_item.added', 'response.output_item.done') and not isinstance(value.get('item'), dict):
            raise ValueError('missing item')
        if result is not None:
            rid = result.get('id')
            if not isinstance(rid, str) or not 1 <= len(rid) <= 200: raise ValueError('response ID')
            if identity is not None and rid != identity: raise ValueError('response changed')
            if result.get('model') != model: raise ValueError('response model')
            identity = rid
        if kind == 'response.created':
            if created or result is None: raise ValueError('duplicate creation')
            if result.get('status') != 'in_progress': raise ValueError('creation status')
            created = True
        if value.get('response_id') is not None and value['response_id'] != identity:
            raise ValueError('response binding')
        item = value.get('item')
        if item is not None:
            iid = item.get('id')
            if (item.get('type') not in ('message', 'reasoning') or not isinstance(iid, str)
                    or not 1 <= len(iid) <= 200): raise ValueError('provider tool or item')
            if kind == 'response.output_item.added':
                if iid in added: raise ValueError('duplicate item')
                position = value.get('output_index')
                if type(position) is not int or position != len(added): raise ValueError('item position')
                positions[iid] = position
                added[iid] = item['type']
            elif kind == 'response.output_item.done':
                if iid not in added or iid in done or added[iid] != item['type']:
                    raise ValueError('item binding')
                if value.get('output_index') != positions[iid]: raise ValueError('item position')
                done[iid] = item
            else: raise ValueError('unexpected item')
        iid = value.get('item_id')
        if iid is not None and (iid not in added or iid in done): raise ValueError('item binding')
        if iid is not None and value.get('output_index') != positions[iid]: raise ValueError('item position')
        if kind.startswith('response.reasoning_'):
            if iid is None or added[iid] != 'reasoning': raise ValueError('reasoning binding')
            if kind.endswith(('.delta', '.done')) and '_part.' not in kind:
                name = 'delta' if kind.endswith('.delta') else 'text'
                index = value.get('summary_index') if 'summary' in kind else value.get('content_index')
                if type(index) is not int or index < 0 or not isinstance(value.get(name), str):
                    raise ValueError('reasoning text schema')
            else:
                part = value.get('part')
                if (type(value.get('summary_index')) is not int or value['summary_index'] < 0
                        or not isinstance(part, dict) or part.get('type') != 'summary_text'
                        or not isinstance(part.get('text'), str)):
                    raise ValueError('reasoning part schema')
        if kind in ('response.content_part.added', 'response.content_part.done'):
            part = value.get('part')
            if (iid is None or added[iid] != 'message' or value.get('content_index') != 0
                    or not isinstance(part, dict) or part.get('type') != 'output_text'
                    or not isinstance(part.get('text'), str)):
                raise ValueError('content binding')
            if kind.endswith('.added'):
                if iid in parts or part['text'] != '': raise ValueError('content order')
                parts[iid] = False
            else:
                if iid not in parts or parts[iid] or part['text'] != text_done.get(iid):
                    raise ValueError('content conflict')
                parts[iid] = True
        if kind in ('response.output_text.delta', 'response.output_text.done'):
            if (iid is None or added[iid] != 'message' or value.get('content_index') != 0
                    or iid not in parts or parts[iid]):
                raise ValueError('text binding')
            if kind.endswith('.delta'):
                if iid in text_done or not isinstance(value.get('delta'), str): raise ValueError('delta binding')
                deltas[iid] = deltas.get(iid, '') + value['delta']
            else:
                if iid in text_done or not isinstance(value.get('text'), str): raise ValueError('text binding')
                if iid in deltas and deltas[iid] != value['text']: raise ValueError('text conflict')
                text_done[iid] = value['text']
        if kind == 'response.completed':
            if (not isinstance(result, dict) or result.get('status') != 'completed'
                    or result.get('error') is not None or result.get('incomplete_details') is not None
                    or result.get('model') != model or not isinstance(result.get('output'), list)
                    or len(result['output']) != len(done) or set(done) != set(added)
                    or any(not isinstance(x, dict) or x.get('id') not in done
                           or done[x['id']] != x for x in result['output'])
                    or len({x['id'] for x in result['output']}) != len(done)):
                raise ValueError('invalid completion')
            for index, output in enumerate(result['output']):
                if positions[output['id']] != index: raise ValueError('final item position')
                if output['type'] == 'message':
                    content = output.get('content')
                    if (not parts.get(output['id']) or output.get('role') != 'assistant' or output.get('status') != 'completed'
                            or not isinstance(content, list) or len(content) != 1
                            or content[0].get('type') != 'output_text'
                            or content[0].get('text') != text_done.get(output['id'])):
                        raise ValueError('final text conflict')
            complete = {k: result[k] for k in ('id', 'status', 'model', 'output')}
            if 'usage' in result: complete['usage'] = result['usage']
    if frame: raise ValueError('unterminated frame')
    if complete is None: raise ValueError('missing completion')
    return complete


def perform(value, token, connection_factory=http.client.HTTPSConnection):
    raw = wire(value['body'])
    timeout = value['timeout']
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise ValueError('timeout')
    if (not isinstance(token, str) or not 1 <= len(token) <= 32768
            or any(c.isspace() or ord(c) < 32 for c in token)):
        raise ValueError('token')
    ca = Path(value['ca_file'])
    if not ca.is_absolute() or not ca.is_file() or ca.is_symlink(): raise ValueError('TLS source')
    pem = ca.read_bytes()
    if len(pem) > 2 * LIMIT or hashlib.sha256(pem).hexdigest() != value['ca_sha256']:
        raise ValueError('TLS binding')
    deadline = time.monotonic() + timeout
    context = ssl.create_default_context(cadata=pem.decode('ascii'))
    connection = connection_factory('api.openai.com', 443, timeout=timeout, context=context)
    try:
        connection.request('POST', '/v1/responses', raw,
            {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
             'Accept': 'text/event-stream', 'Accept-Encoding': 'identity'})
        left = deadline - time.monotonic()
        if left <= 0: raise TimeoutError('deadline')
        if connection.sock: connection.sock.settimeout(left)
        response = connection.getresponse()
        if response.status != 200 or response.getheader('Content-Type', '').split(';')[0].strip() != 'text/event-stream':
            raise ValueError('HTTP refused')
        return read_stream(response, connection, deadline, value['body']['model'])
    finally:
        connection.close()


def main():
    try:
        raw = sys.stdin.buffer.read(3_000_001)
        if len(raw) > 3_000_000: raise ValueError('input limit')
        result = perform(loads(raw), os.environ.get('ATTUNE_CHATGPT_ACCESS_TOKEN'))
        output = json.dumps(result, allow_nan=False).encode()
        if len(output) > LIMIT: raise ValueError('output limit')
        sys.stdout.buffer.write(output)
        return 0
    except Exception:
        sys.stderr.write('plan_request_failed')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
