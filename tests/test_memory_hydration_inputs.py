"""Counterfactual input bindings over guarded synthetic sources; no Redis."""
# qualify: platform

from copy import deepcopy
import hashlib
import json

import pytest

from attune_harness.memory_hydration_capture import capture_sources
from attune_harness.memory_hydration_inputs import (
    ConfigurationObservation, context_commitment, projection_identity,
    source_commitment, source_preimage,
)
from attune_harness.memory_hydration_projection import project_snapshot
from attune_harness.memory_hydration_secrets import REFUSAL
from attune_harness.memory_redis import MemoryRedisUnavailable


def fixture(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'a.md').write_bytes(b'one\r\ntwo\rthree\n')
    config = dict(schema_version=1, actor='fixture-user', owners=['fixture-user'], scopes=['demo'],
                  classifications=['internal'], profiles=['offline'], roots=[
                      dict(id='r', path=str(root.resolve()), tier='personal', owner='fixture-user',
                           scope='demo', classification='internal')],
                  redis=dict(projection='harness-v1', dataset='demo', url_env='FIXTURE_REDIS_URL',
                             password_env='FIXTURE_REDIS_PASSWORD'))
    sources = dict(schema_version=1, sources=[dict(root_id='r', layer='file', corpus='demo', path='.')])
    environment = {'FIXTURE_REDIS_URL': 'redis://fixture-user:fixture-password@localhost:6380/2?db=3',
                   'FIXTURE_REDIS_PASSWORD': 'other-fixture-password'}
    return root, config, sources, environment


def observed(config, sources):
    with capture_sources(config, sources) as snapshot:
        value = deepcopy(snapshot)
    return value


def test_config_commitment_excludes_all_userinfo_secret_values_and_hashes(tmp_path):
    _, config, _, environment = fixture(tmp_path)
    original = ConfigurationObservation(config, environment=environment)
    public = json.dumps(original.commitment(), sort_keys=True)
    for value in ['fixture-user:fixture-password', 'fixture-password', 'other-fixture-password']:
        assert value not in public
        assert hashlib.sha256(value.encode()).hexdigest() not in public
    assert original.commitment()['redis']['endpoint'] == dict(
        scheme='redis', host='localhost', port=6380, path='/2', query=[('db', '3')])
    changed = {**environment, 'FIXTURE_REDIS_URL': 'redis://other:rotated-password@localhost:6380/2?db=3',
               'FIXTURE_REDIS_PASSWORD': 'rotated-other-password'}
    rotated = ConfigurationObservation(config, environment=changed)
    assert original.config_digest == rotated.config_digest
    environment.update(changed)
    with pytest.raises(ValueError, match='changed during'):
        original.verify(config)
    rotated.verify(config)


def test_literal_url_credential_rotation_is_private_but_exact_mutation_refuses(tmp_path):
    _, config, _, environment = fixture(tmp_path)
    config['redis'].pop('url_env')
    config['redis']['url'] = environment['FIXTURE_REDIS_URL']
    original = ConfigurationObservation(config, environment=environment)
    config['redis']['url'] = 'redis://other:rotated-password@localhost:6380/2?db=3'
    with pytest.raises(ValueError, match='changed during'):
        original.verify(config)
    assert ConfigurationObservation(config, environment=environment).config_digest == original.config_digest


@pytest.mark.parametrize('url', [
    'rediss://localhost:6380/2?db=3', 'redis://other.invalid:6380/2?db=3',
    'redis://localhost:6381/2?db=3', 'redis://localhost:6380/3?db=3', 'redis://localhost:6380/2?db=4',
])
def test_actual_exposure_endpoint_changes_commitment(tmp_path, url):
    _, config, _, environment = fixture(tmp_path)
    original = ConfigurationObservation(config, environment=environment)
    changed = {**environment, 'FIXTURE_REDIS_URL': url}
    assert ConfigurationObservation(config, environment=changed).config_digest != original.config_digest


@pytest.mark.parametrize('url', [
    'https://localhost', 'redis://localhost:bad',
    'redis://localhost?socket_timeout=100', 'redis://localhost?db=1&db=2',
])
def test_endpoint_validation_uses_native_readers_same_refusals(tmp_path, url):
    _, config, _, environment = fixture(tmp_path)
    environment['FIXTURE_REDIS_URL'] = url
    with pytest.raises(MemoryRedisUnavailable, match='Native Redis memory'):
        ConfigurationObservation(config, environment=environment)


def test_every_selected_environment_and_config_change_is_revalidated(tmp_path):
    _, config, _, environment = fixture(tmp_path)
    original = ConfigurationObservation(config, environment=environment)
    config['profiles'].append('other')
    with pytest.raises(ValueError, match='changed during'):
        original.verify(config)
    assert original.commitment()['authority']['profiles'] == ['offline']


def test_source_commitment_includes_raw_bytes_even_when_projected_text_is_equal(tmp_path):
    root, config, sources, environment = fixture(tmp_path)
    observation = ConfigurationObservation(config, environment=environment)
    first = observed(config, sources)
    (root / 'a.md').write_bytes(b'one\ntwo\nthree\n')
    second = observed(config, sources)
    assert project_snapshot(first) == project_snapshot(second)
    policy = {'test_policy': 1}
    assert source_commitment(first, observation.config_digest, policy) != source_commitment(
        second, observation.config_digest, policy)
    preimage = source_preimage(first, observation.config_digest, policy)
    assert 'data' not in preimage['entries'][0]
    entry = next(item for item in preimage['entries'] if item['path'] == 'a.md')
    assert entry['sha256'] == hashlib.sha256(b'one\r\ntwo\rthree\n').hexdigest()


@pytest.mark.parametrize('change', [
    'file-version', 'file-mtime', 'directory-identity', 'namespace', 'absence',
    'inventory', 'root-authority', 'selectors', 'config-digest', 'policy',
])
def test_complete_snapshot_counterfactuals_change_input_digest(tmp_path, change):
    _, config, sources, environment = fixture(tmp_path)
    config_digest = ConfigurationObservation(config, environment=environment).config_digest
    first = observed(config, sources)
    second = deepcopy(first)
    policy, other_policy, other_config = {'test_policy': 1}, {'test_policy': 1}, config_digest
    if change == 'file-version':
        second['entries'][('r', 'a.md')]['version'] = 'different-version'
    elif change == 'file-mtime':
        second['entries'][('r', 'a.md')]['mtime_ns'] += 1
    elif change == 'directory-identity':
        second['observations'] = {**second['observations'], 'extra-test-identity': 42}
    elif change == 'namespace':
        second['observations'] = {**second['observations'], 'extra-test-name': 'new.md'}
    elif change == 'absence':
        second['entries'][('r', '.verdicts.jsonl')].update(
            present=True, data=b'', version='new-version', mtime_ns=1)
        second['files'] += 1
    elif change == 'inventory':
        second['inventories'][0].append('new.md')
    elif change == 'root-authority':
        second['roots'][0]['scope'] = 'different'
    elif change == 'selectors':
        second['sources'][0]['corpus'] = 'different'
    elif change == 'config-digest':
        other_config = 'a' * 64
    else:
        other_policy = {'test_policy': 2}
    assert source_commitment(first, config_digest, policy) != source_commitment(
        second, other_config, other_policy)


def test_mapping_insertion_order_does_not_change_canonical_input_digest(tmp_path):
    _, config, sources, environment = fixture(tmp_path)
    config_digest = ConfigurationObservation(config, environment=environment).config_digest
    first = observed(config, sources)
    second = deepcopy(first)
    second['entries'] = dict(reversed(list(second['entries'].items())))
    second['observations'] = dict(reversed(list(second['observations'].items())))
    assert source_commitment(first, config_digest, {'test_policy': 1}) == source_commitment(
        second, config_digest, {'test_policy': 1})


def test_context_changes_and_secret_values_are_distinguishable():
    first = dict(text='fixture context', status='available')
    assert context_commitment(first) == context_commitment(dict(status='available', text='fixture context'))
    assert context_commitment(first) != context_commitment({**first, 'status': 'degraded'})
    with pytest.raises(ValueError, match=REFUSAL):
        context_commitment(dict(text='sk-' + 'Ab1' * 7))


def test_actual_packaged_policy_and_optional_parser_identity_are_bound():
    policy = projection_identity()
    assert policy['index_text_chars'] == 32768
    assert policy['parser']['name'] in ('PyYAML', 'existing-subset')
    assert {'__init__.py', 'memory_controls.py', 'memory_redis.py',
            'memory_hydration_contract.py', 'review_contract.py',
            'memory_hydration_inputs.py'} <= set(policy['modules'])
    assert all(len(value) == 64 for value in policy['modules'].values())


def test_digest_work_honors_shared_budget_before_accepting_result(tmp_path):
    _, config, sources, _ = fixture(tmp_path)
    snapshot = observed(config, sources)
    def expired():
        raise TimeoutError('shared deadline expired')
    with pytest.raises(TimeoutError):
        source_commitment(snapshot, 'a' * 64, {}, check_budget=expired)
    with pytest.raises(TimeoutError):
        context_commitment({}, check_budget=expired)
    with pytest.raises(TimeoutError):
        projection_identity(check_budget=expired)



def test_policy_fingerprint_observes_dependency_changes_additions_removals_and_renames(tmp_path, monkeypatch):
    from attune_harness import memory_hydration_inputs as inputs
    package = tmp_path / 'package'
    package.mkdir()
    (package / '__init__.py').write_text('# synthetic package\n')
    control = package / 'memory_controls.py'
    control.write_text('_SECRETS = []\n')
    nested = package / 'nested'
    nested.mkdir()
    helper = nested / 'helper.py'
    helper.write_text('POLICY = 1\n')
    monkeypatch.setattr(inputs, 'files', lambda name: package)
    first = projection_identity()
    assert set(first['modules']) == {'__init__.py', 'memory_controls.py', 'nested/helper.py'}
    control.write_text('_SECRETS = ["new blocking policy"]\n')
    changed = projection_identity()
    assert first != changed
    assert first['modules']['nested/helper.py'] == changed['modules']['nested/helper.py']
    helper.rename(nested / 'renamed.py')
    renamed = projection_identity()
    assert renamed != changed and 'nested/helper.py' not in renamed['modules']
    (nested / 'extra.py').write_text('POLICY = 2\n')
    added = projection_identity()
    assert added != renamed
    # An executable cache is not a Python source or a new policy file.
    (nested / 'extra.pyc').write_bytes(b'synthetic cache')
    assert projection_identity() == added
    (nested / 'extra.py').unlink()
    assert projection_identity() == renamed
