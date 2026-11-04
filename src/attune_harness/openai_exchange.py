"""Explicit API transport with owner-bound, single-use funding admission."""

import hashlib
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

from .native import NativeError, NativeIdentity, TEXT_SCHEMA, _answer, _json
from .participant_funding import check_issued, claim, release
from .process import invoke


def _redact(value, key, depth=0):
    if depth > 32:
        raise ValueError('API reply exceeds the supported JSON nesting')
    if isinstance(value, str):
        text = value.replace(key, '[redacted]')
        try:
            nested = _json(text)
        except (ValueError, TypeError):
            escaped = text
            pattern = r'\\\\|\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})|\\x([0-9a-fA-F]{2})|\\([0-7]{1,3})'
            def decode(match):
                groups = match.groups()
                number = next((v for v in groups if v is not None), None)
                if number is None:
                    return '\\'
                code = int(number, 8 if groups[3] is not None else 16)
                return chr(code) if code < 128 else match.group()
            for _ in range(32):
                decoded = re.sub(pattern, decode, escaped)
                if key in decoded:
                    return '[redacted credential-bearing text]'
                if decoded == escaped:
                    break
                escaped = decoded
            return text
        clean = _redact(nested, key, depth + 1)
        return json.dumps(clean, ensure_ascii=False) if clean != nested else text
    if isinstance(value, list):
        return [_redact(item, key, depth + 1) for item in value]
    if isinstance(value, dict):
        clean = {}
        for name, item in value.items():
            selected = _redact(name, key, depth + 1)
            if selected in clean:
                raise ValueError('API redaction would create duplicate fields')
            clean[selected] = _redact(item, key, depth + 1)
        return clean
    return value


class OpenAIExchange:
    def __init__(self, *, model, cwd, admission, timeout=60, cancel=None,
                 max_output_bytes=65_536, runner=None):
        check_issued(admission, model)
        if not isinstance(model, str) or not model.strip() or len(model) > 200:
            raise ValueError('An explicit OpenAI model is required')
        self.model, self.cwd, self.admission = model, Path(cwd), admission
        self.timeout, self.cancel = timeout, cancel
        self.max_output_bytes, self.runner = max_output_bytes, runner or invoke
        self.identity = self.last_process = None
        self.usage = None

    def __call__(self, raw):
        data = _json(raw)
        if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
            raise ValueError('Unsupported API request envelope')
        environment = claim(self.admission, self.model, raw)
        receipt = self.admission.receipt
        key = environment['OPENAI_API_KEY']
        body = {'model': self.model, 'input': (
                    'Complete only the accepted task in this JSON request. Do not use tools. '
                    'Return an object with one string field named text.\n' + raw),
                'tools': [], 'store': False, 'max_output_tokens': 4096,
                'text': {'format': {'type': 'json_schema', 'name': 'harness_text',
                                    'strict': True, 'schema': TEXT_SCHEMA}}}
        argv = (sys.executable, '-I', '-S', str(Path(__file__).with_name('openai_worker.py')))
        receipt['dispatch_outcome'] = 'unknown'
        try:
            try:
                result = self.runner(argv, json.dumps({'body': body, 'timeout': self.timeout}),
                                     cwd=self.cwd, timeout=self.timeout, cancel=self.cancel,
                                     max_output_bytes=self.max_output_bytes,
                                     environment=environment)
            except Exception:
                raise NativeError('OpenAI transport failed; external effects remain unknown',
                                  failure='transport_error') from None
            # No raw provider/process diagnostics escape the API boundary.
            self.last_process = replace(result, stdout='', stderr='')
            if result.failure or result.returncode != 0:
                if result.failure in ('not_found', 'launch_failed', 'cancelled_before_start'):
                    receipt['dispatch_outcome'] = 'not_started'
                raise NativeError('OpenAI request did not deliver a validated result',
                                  failure=result.failure or 'nonzero_exit',
                                  process_stopped=result.returncode is not None)
            value = _redact(_json(result.stdout.replace(key, '[redacted]')), key)
            if (not isinstance(value, dict) or value.get('status') != 'completed'
                    or value.get('error') is not None or value.get('incomplete_details') is not None
                    or value.get('model') != self.model):
                raise ValueError('OpenAI response is incomplete or differs from the selected model')
            identifier = value.get('id')
            if isinstance(identifier, str):
                identifier = identifier.replace(key, '[redacted]')
            if not isinstance(identifier, str) or re.fullmatch(r'resp_[A-Za-z0-9_-]{1,180}', identifier) is None:
                raise ValueError('OpenAI response omitted its identity')
            output = value.get('output')
            if not isinstance(output, list) or any(not isinstance(item, dict) or
                    item.get('type') not in ('message', 'reasoning') for item in output):
                raise ValueError('Unsupported OpenAI output')
            messages = [item for item in output if item['type'] == 'message']
            if (len(messages) != 1 or messages[0].get('role') != 'assistant'
                    or messages[0].get('status') != 'completed'):
                raise ValueError('Missing completed OpenAI assistant message')
            content = messages[0].get('content')
            if (not isinstance(content, list) or len(content) != 1
                    or not isinstance(content[0], dict) or content[0].get('type') != 'output_text'
                    or not isinstance(content[0].get('text'), str)):
                raise ValueError('OpenAI response omitted structured text')
            text = _answer(_json(content[0]['text'])).replace(key, '[redacted]')
            from .funding_usage import normalize
            self.usage = normalize(value.get('usage'))
            self.identity = NativeIdentity('openai', identifier, (self.model,))
            receipt['dispatch_outcome'] = 'completed'
            return json.dumps({'version': 1, 'request_digest': hashlib.sha256(raw.encode()).hexdigest(),
                               'text': text})
        except NativeError:
            raise
        except Exception:
            # Parsing errors can include attacker-controlled data; expose none.
            raise NativeError('OpenAI response failed validation; usage and effects may be unknown',
                              failure='invalid_response',
                              process_stopped=self.last_process is not None and
                                              self.last_process.returncode is not None) from None
        finally:
            # Drop the private reference after this single attempt.
            release(self.admission)
