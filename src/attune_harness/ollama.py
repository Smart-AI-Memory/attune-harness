"""Explicit, pinned local inference. No downloads, credentials, proxies or fallback."""
import hashlib
import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass

from .adapters import _unique_object

ENDPOINT = 'http://127.0.0.1:11434/api/'
MAX_RESPONSE = 1_048_576
MAX_MODEL_METADATA = 16_777_216


class LocalModelError(RuntimeError):
    """Local inference unavailable, incomplete, or inconsistent with its pin."""


def validate_output_budget(num_ctx, num_predict):
    for name, value in (('num_ctx', num_ctx), ('num_predict', num_predict)):
        if type(value) is not int or value < 1:
            raise ValueError(name + ' must be a positive integer')
    if not 1024 <= num_ctx <= 16384 or num_predict >= num_ctx - 512:
        raise ValueError('Local context/output budget outside supported bounds; reserve context for input and framing')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LocalModelError('Local model endpoint attempted a redirect')


def parse(raw):
    def invalid(value):
        raise ValueError('Non-finite JSON value: ' + value)
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=invalid)


def local_request(endpoint, payload=None, *, timeout=60):
    if endpoint not in ('tags', 'version', 'generate', 'show'):
        raise ValueError('Unsupported local model endpoint')
    body = json.dumps(payload, allow_nan=False).encode() if payload is not None else None
    if body is not None and len(body) > 65_536:
        raise ValueError('Local model request exceeds 64 KiB')
    request = urllib.request.Request(ENDPOINT + endpoint, data=body, headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    limit = MAX_MODEL_METADATA if endpoint == 'show' else MAX_RESPONSE
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(limit + 1)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4097)
        message = detail[:4096].decode('utf-8', errors='replace')
        if len(detail) > 4096:
            message += ' [truncated]'
        raise LocalModelError(f'Local model HTTP {exc.code}; no retry was performed: {message}') from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LocalModelError(f'Local model request failed; no retry was performed: {exc}') from exc
    if len(raw) > limit:
        raise LocalModelError(f'Local model response exceeds {limit} bytes')
    value = parse(raw.decode('utf-8'))
    if not isinstance(value, dict) or 'error' in value:
        raise LocalModelError(f'Local model returned an invalid/error response: {value}')
    return value


@dataclass(frozen=True)
class ModelPin:
    name: str
    digest: str
    server_version: str

    def __post_init__(self):
        if (not isinstance(self.name, str) or not self.name or len(self.name) > 200
                or 'cloud' in self.name.lower() or not isinstance(self.server_version, str) or not self.server_version
                or not isinstance(self.digest, str) or len(self.digest) != 64
                or any(c not in '0123456789abcdef' for c in self.digest)):
            raise ValueError('Require an explicit local model name, SHA256 digest and server version')


class LocalModel:
    def __init__(self, pin: ModelPin, *, request=local_request, timeout=60, tokenizer=None):
        if not isinstance(pin, ModelPin):
            raise TypeError('pin must be ModelPin')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 1 <= timeout <= 120:
            raise ValueError('timeout must be finite in 1..120 seconds')
        self.pin, self.request, self.timeout = pin, request, timeout
        if tokenizer is not None and tokenizer.pin != pin:
            raise ValueError('Tokenizer differs from the accepted model pin')
        self.tokenizer = tokenizer
        self.last_context_accounting = None
        self.last_response, self.last_request, self.generation_attempted = None, None, False

    def metadata(self):
        version = self.request('version', timeout=self.timeout)
        tags = self.request('tags', timeout=self.timeout)
        if version.get('version') != self.pin.server_version:
            raise LocalModelError('Ollama server version differs from the accepted pin')
        matches = [m for m in tags.get('models', []) if m.get('name') == self.pin.name]
        if len(matches) != 1:
            raise LocalModelError('Pinned model is not present exactly once; no download was attempted')
        model = matches[0]
        if (model.get('digest') != self.pin.digest or model.get('details', {}).get('format') != 'gguf'
                or type(model.get('size')) is not int or model['size'] <= 0
                or model.get('remote_model') or model.get('remote_host')
                or 'completion' not in model.get('capabilities', [])):
            raise LocalModelError('Pinned local model artifact is missing, changed, remote, or not generative')
        return {'version': version, 'model': model}

    def generate(self, prompt, *, system, schema, seed, options):
        self.last_response, self.last_request, self.generation_attempted = None, None, False
        self.last_context_accounting = None
        if not isinstance(prompt, str) or not prompt.strip() or not isinstance(system, str):
            raise ValueError('Require prompt and system text')
        if len((prompt + system).encode('utf-8')) > 65_536:
            raise ValueError('Input text exceeds the local request transport budget')
        if type(seed) is not int or not 0 <= seed < 2**31:
            raise ValueError('seed must be a nonnegative 31-bit integer')
        allowed = {'temperature', 'num_ctx', 'num_predict', 'top_k', 'top_p', 'repeat_penalty'}
        if not isinstance(options, dict) or set(options) - allowed:
            raise ValueError('Unsupported model runtime option')
        validate_output_budget(options.get('num_ctx'), options.get('num_predict'))
        for name, value in options.items():
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('Runtime options must be finite nonnegative numbers')
        if not isinstance(schema, dict) or schema.get('type') != 'object':
            raise ValueError('An explicit object output schema is required')
        input_units = (self.tokenizer.count(prompt, system) if self.tokenizer is not None
                       else len((prompt + system).encode('utf-8')))
        if type(input_units) is not int or input_units < 1:
            raise ValueError('Tokenizer returned an invalid input count')
        self.last_context_accounting = {
            **(self.tokenizer.identity if self.tokenizer is not None else
               {'kind': 'conservative_utf8_bytes', 'reason': 'No qualified tokenizer selected'}),
            'input_units': input_units, 'output_token_reserve': options['num_predict'],
            'framing_margin': 512, 'context_tokens': options['num_ctx'],
            'remaining_after_reserves': options['num_ctx'] - input_units - options['num_predict'] - 512}
        if self.last_context_accounting['remaining_after_reserves'] < 0:
            raise ValueError('Prompt exceeds the local context budget (' + self.last_context_accounting['kind'] + ')')
        before = self.metadata()
        payload = {'model': self.pin.name, 'system': system, 'prompt': prompt, 'format': schema,
                   'stream': False, 'keep_alive': '5m', 'truncate': False, 'shift': False,
                   'options': {**options, 'seed': seed}}
        self.last_request = payload
        self.generation_attempted = True
        result = self.request('generate', payload, timeout=self.timeout)
        self.last_response = result
        if result.get('model') != self.pin.name or result.get('done') is not True or result.get('done_reason') != 'stop':
            raise LocalModelError('Local generation did not finish with the accepted model; output may be truncated')
        if not isinstance(result.get('response'), str) or not result['response'].strip():
            raise LocalModelError('Local generation returned no output')
        for name in ('prompt_eval_count', 'eval_count', 'total_duration', 'load_duration', 'prompt_eval_duration', 'eval_duration'):
            if type(result.get(name)) is not int or result[name] < 0:
                raise LocalModelError('Local generation lacks valid usage/timing: ' + name)
        if self.tokenizer is not None and result['prompt_eval_count'] != input_units:
            raise LocalModelError('Server input token count differs from the qualified tokenizer; output is unaccepted')
        if result['prompt_eval_count'] + options['num_predict'] + 512 > options['num_ctx']:
            raise LocalModelError('Server input count exceeds the reserved context budget')
        if self.metadata() != before:
            raise LocalModelError('Pinned local model metadata changed during the invocation')
        return {**result, 'local_identity': {'model': self.pin.name, 'digest': self.pin.digest,
                                           'server_version': self.pin.server_version}}


class LocalJsonExchange:
    """Wrap one local generation for the existing JsonParticipant wire contract."""
    def __init__(self, model, *, system, schema, seed, options):
        self.model, self.system, self.schema = model, system, schema
        self.seed, self.options, self.last_generation = seed, options, None

    def __call__(self, raw):
        self.last_generation = None
        request = parse(raw)
        if set(request) != {'version', 'attempt'} or type(request['version']) is not int or request['version'] != 1:
            raise ValueError('Expected a JSON attempt version 1')
        result = self.model.generate(request['attempt']['task']['objective'], system=self.system,
                                     schema=self.schema, seed=self.seed, options=self.options)
        self.last_generation = result
        return json.dumps({'version': 1, 'request_digest': hashlib.sha256(raw.encode()).hexdigest(),
                           'text': result['response']})
