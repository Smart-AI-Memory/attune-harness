"""Usage evidence retains reported counts and refuses false billing precision."""
# qualify: platform

import copy
import json

import pytest


@pytest.mark.parametrize('extra', [
    {'total_tokens': 999}, {'total_tokens': True},
    {'output_tokens_details': {'reasoning_tokens': 8}},
    {'output_tokens_details': {'reasoning_tokens': False}},
    {'output_tokens_details': None},
])
def test_contradictory_optional_totals_and_reasoning_remain_unknown(extra):
    from attune_harness.funding_usage import normalize
    result = normalize({'input_tokens': 13, 'output_tokens': 7, **extra})
    assert result['state'] == 'unknown' and result['reason'] == 'invalid'
    assert result['input_tokens'] is None and result['output_tokens'] is None

from attune_harness.funding_usage import normalize, validate


def reported(input_tokens=100, output_tokens=20, cached_input_tokens=40):
    return {'profile': 'native-usage-v1', 'input_tokens': input_tokens,
            'output_tokens': output_tokens, 'cached_input_tokens': cached_input_tokens,
            'cache_creation_tokens': None, 'provider_reported_cost_usd': None,
            'billed_cost_usd': None, 'remaining_balance': None,
            'state': 'reported', 'reason': None}


def unknown(reason):
    return {**reported(None, None, None), 'state': 'unknown', 'reason': reason}


def test_cache_is_a_subset_and_unknown_categories_do_not_become_claims():
    raw = {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120,
           'input_tokens_details': {'cached_tokens': 40, 'future_category': 99},
           'provider_reported_cost_usd': 9.99, 'billed_cost_usd': 10,
           'remaining_balance': 350, 'extra': {'account': 'unretained-sentinel'}}
    before = copy.deepcopy(raw)
    value = normalize(raw)
    assert value == reported()
    assert value['input_tokens'] == 100  # Cached input is already part of input.
    assert validate(value) is value
    assert raw == before
    assert 'unretained-sentinel' not in json.dumps(value, allow_nan=False)


@pytest.mark.parametrize('details', [None, {}, {'future_category': 7}])
def test_optional_cache_details_do_not_invent_a_zero(details):
    raw = {'input_tokens': 9, 'output_tokens': 2}
    if details is not None:
        raw['input_tokens_details'] = details
    assert normalize(raw) == reported(9, 2, None)


@pytest.mark.parametrize('count', [0, 10**12])
def test_counter_bounds_are_inclusive(count):
    value = normalize({'input_tokens': count, 'output_tokens': count,
                       'input_tokens_details': {'cached_tokens': count}})
    assert value == reported(count, count, count)
    assert validate(value) is value


@pytest.mark.parametrize('raw,reason', [
    (None, 'missing'), ({}, 'missing'), ({'unselected': 1}, 'missing'),
    ({'input_tokens_details': {}}, 'missing'),
    ({'input_tokens': 7}, 'partial'), ({'output_tokens': 2}, 'partial'),
    ({'input_tokens_details': {'cached_tokens': 0}}, 'partial'),
    ({'input_tokens': 7, 'input_tokens_details': {'cached_tokens': 3}}, 'partial'),
])
def test_missing_and_partial_usage_retains_no_counts(raw, reason):
    value = normalize(raw)
    assert value == unknown(reason)
    assert validate(value) is value


INVALID_COUNTS = [True, False, -1, 1.0, 0.0, '7', None, 10**12 + 1,
                  float('nan'), float('inf'), float('-inf'), [], {}]


@pytest.mark.parametrize('count', INVALID_COUNTS)
@pytest.mark.parametrize('category', ['input_tokens', 'output_tokens', 'cached_tokens'])
def test_invalid_selected_counter_discards_all_usage(category, count):
    raw = {'input_tokens': 100, 'output_tokens': 20,
           'input_tokens_details': {'cached_tokens': 40}}
    target = raw['input_tokens_details'] if category == 'cached_tokens' else raw
    target[category] = count
    assert normalize(raw) == unknown('invalid')


@pytest.mark.parametrize('raw', [
    True, [], 'unretained-sentinel', 1,
    {'input_tokens': 10, 'output_tokens': 2, 'input_tokens_details': None},
    {'input_tokens': 10, 'output_tokens': 2, 'input_tokens_details': []},
    {'input_tokens': 10, 'output_tokens': 2, 'input_tokens_details': {'cached_tokens': 11}},
    {'input_tokens': 10, 'input_tokens_details': {'cached_tokens': 11}},
    {'input_tokens': False},
])
def test_malformed_usage_and_contradictory_cache_are_unknown(raw):
    assert normalize(raw) == unknown('invalid')


@pytest.mark.parametrize('field', list(reported()))
def test_saved_usage_requires_every_field(field):
    value = reported()
    del value[field]
    with pytest.raises(ValueError):
        validate(value)


@pytest.mark.parametrize('field,value', [
    ('profile', 'other-v1'), ('state', 'ready'), ('reason', 'missing'),
    ('cache_creation_tokens', 0), ('provider_reported_cost_usd', 0),
    ('billed_cost_usd', 0.0), ('remaining_balance', 350),
    ('input_tokens', None), ('output_tokens', None), ('cached_input_tokens', 101),
])
def test_saved_reported_usage_refuses_invalid_state_and_claims(field, value):
    saved = reported()
    saved[field] = value
    with pytest.raises(ValueError):
        validate(saved)


@pytest.mark.parametrize('count', INVALID_COUNTS)
@pytest.mark.parametrize('field', ['input_tokens', 'output_tokens', 'cached_input_tokens'])
def test_saved_counter_validation_is_strict(field, count):
    if field == 'cached_input_tokens' and count is None:
        assert validate(reported(cached_input_tokens=None))['cached_input_tokens'] is None
    else:
        saved = reported()
        saved[field] = count
        with pytest.raises(ValueError):
            validate(saved)


@pytest.mark.parametrize('reason', ['missing', 'partial', 'invalid'])
def test_saved_unknown_usage_cannot_retain_reported_counts(reason):
    saved = unknown(reason)
    saved['input_tokens'] = 0
    with pytest.raises(ValueError):
        validate(saved)


@pytest.mark.parametrize('reason', [None, 'other', True, 0, [], {}])
def test_unknown_usage_requires_allowlisted_reason(reason):
    with pytest.raises(ValueError):
        validate(unknown(reason))


@pytest.mark.parametrize('value', [None, True, [], 'unretained-sentinel',
                                   {**reported(), 'extra': 'unretained-sentinel'}])
def test_saved_evidence_rejects_other_shapes_without_echo(value):
    with pytest.raises(ValueError) as error:
        validate(value)
    assert 'unretained-sentinel' not in str(error.value)


def test_validation_preserves_saved_evidence_and_json_round_trip():
    value = reported(10**12, 0, None)
    before = copy.deepcopy(value)
    assert validate(value) is value
    assert value == before
    assert validate(json.loads(json.dumps(value, allow_nan=False))) == value
