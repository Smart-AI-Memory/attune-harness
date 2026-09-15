"""Adversarial checks for the disposable evaluator, not a production cache API."""
import copy
import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parent.parent / 'experiments/e2/policy.py'
spec = importlib.util.spec_from_file_location('e2_policy_tests', path)
policy = importlib.util.module_from_spec(spec); spec.loader.exec_module(policy)


@pytest.fixture
def observed():
    descriptor = {'tool': 'evidence.search', 'adapter': 'adapter-a', 'lifecycle': 'enabled',
        'grants': ['evidence.search'], 'declared_tools': ['evidence.search'],
        'dependencies': {'attune-rag': '1.2.0'}, 'required_dependencies': {'attune-rag': '1.2.0'},
        'artifact': {'digest': 'artifact-a', 'version': '0.1.0'}, 'corpus_root': '/local/corpus',
        'arguments': {'query': 'quartz', 'k': 3}, 'sources': {'guide.md': 'source-a'}}
    result = {'operation': 'retrieve', 'status': 'retrieved',
        'dependency': {'name': 'attune-rag', 'version': '1.2.0'}, 'query': 'quartz', 'k': 3,
        'extension': {'tool': 'evidence.search', 'artifact_digest': 'artifact-a', 'version': '0.1.0'},
        'corpus': {'root': '/local/corpus'}, 'sources': [{'path': 'guide.md', 'sha256': 'source-a'}]}
    observation = {'descriptor': copy.deepcopy(descriptor), 'result': result}
    observation['digest'] = policy.fingerprint(observation)
    return descriptor, observation


def test_matching_historical_success_is_the_candidate_claim_not_oracle_proof(observed):
    current, observation = observed
    result = policy.decide('version-bound-cache', current, observation)
    assert result['verified_availability_claim'] and result['status'] == 'verified_available'
    # Force an independently failing oracle: the score must expose, not hide, the miss.
    assert policy.score(result, False)['false_verified_availability_claim']


@pytest.mark.parametrize('key,value', [('adapter', 'adapter-b'), ('artifact', {'digest': 'artifact-b', 'version': '0.2.0'}),
    ('sources', {'guide.md': 'source-b'}), ('arguments', {'query': 'different', 'k': 3})])
def test_changed_identity_and_scope_defer_without_reusing_success(observed, key, value):
    current, observation = observed
    current[key] = value
    result = policy.decide('version-bound-cache', current, observation)
    assert result['status'] == 'needs_probe' and not result['verified_availability_claim']
    metric = policy.score(result, True)
    assert metric['deferred_usable_case'] and not metric['unnecessary_rejection']


@pytest.mark.parametrize('key,value,status', [('lifecycle', 'disabled', 'denied'), ('grants', [], 'denied'),
    ('dependencies', {'attune-rag': None}, 'unavailable')])
def test_matching_history_cannot_override_current_guard(observed, key, value, status):
    current, observation = observed
    current[key] = value
    result = policy.decide('version-bound-cache', current, observation)
    assert result['status'] == status and not result['predicted_usable']
    assert policy.score(result, True)['unnecessary_rejection']


@pytest.mark.parametrize('mutation', ['source', 'status', 'artifact', 'empty', 'dependency', 'corpus', 'query', 'seal'])
def test_misleading_observation_does_not_establish_success(observed, mutation):
    current, observation = observed
    value = observation['result']
    if mutation == 'source': value['sources'][0]['sha256'] = 'wrong'
    elif mutation == 'status': value['status'] = 'verified'
    elif mutation == 'artifact': value['extension']['artifact_digest'] = 'different'
    elif mutation == 'empty': value['sources'] = []
    elif mutation == 'dependency': value['dependency']['version'] = '0.0.0'
    elif mutation == 'corpus': value['corpus']['root'] = '/outside'
    elif mutation == 'query': value['query'] = 'other'
    else: observation['digest'] = 'tampered'
    if mutation != 'seal':
        observation['digest'] = policy.fingerprint({key: observation[key] for key in ('descriptor', 'result')})
    result = policy.decide('version-bound-cache', current, observation)
    assert result['status'] == 'needs_probe' and not result['verified_availability_claim']


def test_declaration_prediction_is_not_misreported_as_a_verified_claim(observed):
    current, _ = observed
    result = policy.decide('declaration-only', current, None)
    score = policy.score(result, False)
    assert score['false_usable_prediction'] and not score['false_verified_availability_claim']
    assert not score['unnecessary_rejection']


def test_unknown_policy_is_not_silently_selected(observed):
    with pytest.raises(ValueError, match='Unknown'):
        policy.decide('unknown', *observed)
