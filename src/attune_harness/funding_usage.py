"""Normalize reported token counts without inferring charges or balances."""

PROFILE = 'native-usage-v1'
MAX_TOKENS = 10**12
_COUNTERS = ('input_tokens', 'output_tokens', 'cached_input_tokens')
_UNSUPPORTED = ('cache_creation_tokens', 'provider_reported_cost_usd',
                'billed_cost_usd', 'remaining_balance')
_FIELDS = {'profile', *_COUNTERS, *_UNSUPPORTED, 'state', 'reason'}


def _counter(value):
    return type(value) is int and 0 <= value <= MAX_TOKENS


def _unknown(reason):
    return {'profile': PROFILE, **dict.fromkeys((*_COUNTERS, *_UNSUPPORTED)),
            'state': 'unknown', 'reason': reason}


def normalize(raw):
    """Read selected OpenAI Responses usage fields; discard incomplete counts."""
    if raw is None:
        return _unknown('missing')
    if not isinstance(raw, dict):
        return _unknown('invalid')
    for name in ('input_tokens', 'output_tokens'):
        if name in raw and not _counter(raw[name]):
            return _unknown('invalid')

    cached = None
    if 'input_tokens_details' in raw:
        details = raw['input_tokens_details']
        if not isinstance(details, dict):
            return _unknown('invalid')
        if 'cached_tokens' in details:
            cached = details['cached_tokens']
            if not _counter(cached):
                return _unknown('invalid')

    if cached is not None and 'input_tokens' in raw and cached > raw['input_tokens']:
        return _unknown('invalid')
    if 'input_tokens' not in raw or 'output_tokens' not in raw:
        missing = not any(name in raw for name in ('input_tokens', 'output_tokens'))
        return _unknown('missing' if missing and cached is None else 'partial')
    if 'total_tokens' in raw and (not _counter(raw['total_tokens'])
            or raw['total_tokens'] != raw['input_tokens'] + raw['output_tokens']):
        return _unknown('invalid')
    if 'output_tokens_details' in raw:
        details = raw['output_tokens_details']
        if not isinstance(details, dict):
            return _unknown('invalid')
        reasoning = details.get('reasoning_tokens')
        if 'reasoning_tokens' in details and (not _counter(reasoning) or reasoning > raw['output_tokens']):
            return _unknown('invalid')
    return {'profile': PROFILE, 'input_tokens': raw['input_tokens'],
            'output_tokens': raw['output_tokens'], 'cached_input_tokens': cached,
            **dict.fromkeys(_UNSUPPORTED), 'state': 'reported', 'reason': None}


def validate(value):
    """Validate saved usage evidence without changing it or accepting cost claims."""
    if not isinstance(value, dict) or set(value) != _FIELDS:
        raise ValueError('Invalid usage evidence fields')
    if value['profile'] != PROFILE or any(value[name] is not None for name in _UNSUPPORTED):
        raise ValueError('Invalid usage profile or unsupported cost and cache evidence')
    if value['state'] == 'unknown':
        if value['reason'] not in ('missing', 'partial', 'invalid') or any(
                value[name] is not None for name in _COUNTERS):
            raise ValueError('Unknown usage must retain a reason and no counts')
    elif value['state'] == 'reported':
        if value['reason'] is not None or not all(
                _counter(value[name]) for name in ('input_tokens', 'output_tokens')):
            raise ValueError('Reported usage requires valid input and output counts')
        cached = value['cached_input_tokens']
        if cached is not None and (not _counter(cached) or cached > value['input_tokens']):
            raise ValueError('Invalid cached input count')
    else:
        raise ValueError('Unsupported usage state')
    return value
