"""Composition and fresh-observation controls over synthetic sources only."""
# qualify: platform

from contextlib import contextmanager
from copy import deepcopy
import json

import pytest

from attune_harness import memory_hydration as owner
from attune_harness.memory_hydration_contract import validate_manifest
from attune_harness.memory_hydration_secrets import REFUSAL


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path / 'source'
    (root / 'curated').mkdir(parents=True)
    (root / 'rules' / 'empty').mkdir(parents=True)
    (root / 'notes').mkdir()
    (root / 'curated' / 'n.md').write_text(
        '---\ncurated: true\nnode_id: n\nstatus: active\n---\nA synthetic private body.\n',
        encoding='utf-8')
    (root / 'notes' / 'a.md').write_text('A synthetic pointer body.\n', encoding='utf-8')
    (root / 'lessons.md').write_text('- **Inspect**: Read the entire input.\n', encoding='utf-8')
    (root / 'rules' / 'r.md').write_text('# Rule\nVerify the result.\n', encoding='utf-8')
    config = dict(schema_version=1, actor='fixture-user', owners=['fixture-user'], scopes=['demo'],
                  classifications=['internal'], profiles=['offline'], roots=[
                      dict(id='r', path=str(root.resolve()), tier='personal', owner='fixture-user',
                           scope='demo', classification='internal')],
                  redis=dict(projection='harness-v1', dataset='demo',
                             url_env='FIXTURE_REDIS_URL', password_env='FIXTURE_REDIS_PASSWORD'))
    sources = dict(schema_version=1, sources=[
        dict(root_id='r', layer=layer, corpus=corpus, path=path)
        for layer, corpus, path in [('curated', 'nodes', 'curated'), ('file', 'demo', 'notes'),
                                   ('lesson', 'lessons', 'lessons.md'), ('rule', 'rules', 'rules')]])
    environment = dict(FIXTURE_REDIS_URL='redis://fixture:private-password@localhost:6379/2',
                       FIXTURE_REDIS_PASSWORD='other-private-password')
    return root, config, sources, environment


def prepared(inputs, *, budget=lambda: None):
    _, config, sources, environment = inputs
    return owner.PreparedHydration(config, sources, 'synthetic context',
                                   check_budget=budget, environment=environment)


def test_all_layers_materialize_exact_self_counted_manifest_without_a_client(inputs, monkeypatch):
    from attune_harness import memory_hydration_redis, memory_redis
    def forbidden(*args, **kwargs):
        pytest.fail('Private preparation attempted Redis access')
    monkeypatch.setattr(memory_hydration_redis, 'connect', forbidden)
    monkeypatch.setattr(memory_redis.RedisMemory, '__init__', forbidden)
    value = prepared(inputs)
    assert value.summary()['counts'] == dict(curated=1, file=1, lesson=1, rule=1)
    resources, manifest, raw = value.materialize(
        'a' * 32, None, 'b' * 32, '2026-10-26T00:00:00Z')
    assert len(manifest) == 11
    assert validate_manifest(raw, manifest['binding'], manifest['function_digest']) == manifest
    prefix = 'attune:harness:hydration:demo:' + 'a' * 32 + ':'
    assert next(r for r in resources if r['key'] == prefix + 'node:n')['fields']['description'] == (
        'A synthetic private body.')
    assert next(r for r in resources if r['key'] == prefix + 'context')['value'] == 'synthetic context'
    measured = len((prefix + 'manifest').encode()) + len(raw.encode())
    for item in resources:
        measured += len(item['key'].encode())
        if item['kind'] == 'hash':
            measured += sum(len(k.encode()) + len(v.encode()) for k, v in item['fields'].items())
        elif item['kind'] == 'string':
            measured += len(item['value'].encode())
        else:
            key = 'items' if item['kind'] == 'list' else 'members'
            measured += sum(len(v.encode()) for v in item[key])
    assert measured == manifest['projection_bytes']
    value.verify_fresh(inputs[1], inputs[2], 'synthetic context')


def test_summary_contains_no_source_paths_bodies_context_or_credentials(inputs):
    value = prepared(inputs)
    text = json.dumps(value.summary())
    for private in [str(inputs[0]), 'A synthetic private body', 'A synthetic pointer body',
                    'synthetic context', 'private-password', 'other-private-password', 'localhost']:
        assert private not in text
    summary = value.summary()
    summary['counts']['curated'] = 99
    assert value.summary()['counts']['curated'] == 1
    assert value.summary()['index_text_chars'] == 32768


@pytest.mark.parametrize('change', [
    'addition', 'absence-to-empty', 'empty-to-absence', 'directory-identity',
    'raw-newline', 'safe-body', 'selector-order-change',
])
def test_complete_fresh_observation_refuses_changes_without_refreshing(inputs, change):
    root, config, sources, _ = inputs
    if change == 'empty-to-absence':
        (root / 'summaries_by_path.json').write_text('{}', encoding='utf-8')
    value = prepared(inputs)
    original = value.summary()
    if change == 'addition':
        (root / 'notes' / 'new.md').write_text('New pointer.', encoding='utf-8')
    elif change == 'absence-to-empty':
        (root / 'summaries_by_path.json').write_text('{}', encoding='utf-8')
    elif change == 'empty-to-absence':
        (root / 'summaries_by_path.json').unlink()
    elif change == 'directory-identity':
        (root / 'rules' / 'empty').rename(root / 'old-directory')
        (root / 'rules' / 'empty').mkdir()
    elif change == 'raw-newline':
        (root / 'notes' / 'a.md').write_bytes(b'A synthetic pointer body.\r\n')
    elif change == 'safe-body':
        (root / 'notes' / 'a.md').write_text('Changed pointer.', encoding='utf-8')
    else:
        sources['sources'][1]['corpus'] = 'different'
    with pytest.raises(ValueError, match='inputs changed'):
        value.verify_fresh(config, sources, 'synthetic context')
    assert value.summary() == original


@pytest.mark.parametrize('change', ['context', 'selected-env', 'config', 'policy', 'bundle'])
def test_other_fresh_inputs_are_bound(inputs, monkeypatch, change):
    _, config, sources, environment = inputs
    value = prepared(inputs)
    context = 'synthetic context'
    if change == 'context':
        context += ' changed'
    elif change == 'selected-env':
        environment['FIXTURE_REDIS_PASSWORD'] = 'rotated-private-password'
    elif change == 'config':
        config['actor'] = 'different'
    elif change == 'policy':
        original = owner.projection_identity
        def changed(**kwargs):
            return {**original(**kwargs), 'changed': True}
        monkeypatch.setattr(owner, 'projection_identity', changed)
    else:
        monkeypatch.setattr(owner, 'function_digest', lambda: 'c' * 64)
    with pytest.raises(ValueError, match='changed'):
        value.verify_fresh(config, sources, context)


def test_capture_context_exit_must_succeed_before_preparation_returns(inputs, monkeypatch):
    actual = owner.capture_sources
    @contextmanager
    def fails_after_consumption(*args, **kwargs):
        with actual(*args, **kwargs) as snapshot:
            yield snapshot
        raise ValueError('synthetic exit refusal')
    monkeypatch.setattr(owner, 'capture_sources', fails_after_consumption)
    with pytest.raises(ValueError, match='synthetic exit refusal'):
        prepared(inputs)


def test_real_source_mutation_during_projection_refuses_before_acceptance(inputs, monkeypatch):
    actual = owner.project_snapshot
    def changed(*args, **kwargs):
        result = actual(*args, **kwargs)
        (inputs[0] / 'notes' / 'a.md').write_text('Changed after capture.', encoding='utf-8')
        return result
    monkeypatch.setattr(owner, 'project_snapshot', changed)
    with pytest.raises(ValueError, match='changed'):
        prepared(inputs)


def test_environment_mutation_during_projection_refuses(inputs, monkeypatch):
    actual = owner.project_snapshot
    def changed(*args, **kwargs):
        result = actual(*args, **kwargs)
        inputs[3]['FIXTURE_REDIS_PASSWORD'] = 'rotated'
        return result
    monkeypatch.setattr(owner, 'project_snapshot', changed)
    with pytest.raises(ValueError, match='configuration changed'):
        prepared(inputs)


def test_full_context_secret_is_refused(inputs):
    token = 'sk-' + 'Ab1' * 7
    with pytest.raises(ValueError, match=REFUSAL):
        owner.PreparedHydration(inputs[1], inputs[2], 'synthetic context ' + token,
                                check_budget=lambda: None, environment=inputs[3])


@pytest.mark.parametrize('method', ['prepare', 'summary', 'materialize', 'verify_fresh'])
def test_original_budget_failure_propagates_without_reset(inputs, method):
    class Expired(RuntimeError):
        pass
    expired = False
    checks = 0
    def budget():
        nonlocal checks
        checks += 1
        if expired:
            raise Expired('synthetic original deadline')
    if method == 'prepare':
        expired = True
        with pytest.raises(Expired):
            prepared(inputs, budget=budget)
        assert checks == 1
        return
    value = prepared(inputs, budget=budget)
    expired = True
    with pytest.raises(Expired):
        if method == 'summary':
            value.summary()
        elif method == 'materialize':
            value.materialize('a' * 32, None, 'b' * 32, '2026-10-26T00:00:00Z')
        else:
            value.verify_fresh(inputs[1], inputs[2], 'synthetic context')


@pytest.mark.parametrize('phase', ['prepare', 'verify_fresh'])
@pytest.mark.parametrize('change', ['environment', 'sources'])
def test_final_policy_observation_cannot_hide_selected_input_mutation(inputs, monkeypatch, phase, change):
    value = prepared(inputs) if phase == 'verify_fresh' else None
    actual = owner.projection_identity
    calls = 0
    def mutate_at_final_observation(**kwargs):
        nonlocal calls
        result = actual(**kwargs)
        calls += 1
        if calls == 2:
            if change == 'environment':
                inputs[3]['FIXTURE_REDIS_PASSWORD'] = 'changed-during-policy-read'
            else:
                inputs[2]['sources'][1]['corpus'] = 'changed'
        return result
    monkeypatch.setattr(owner, 'projection_identity', mutate_at_final_observation)
    with pytest.raises(ValueError, match='configuration changed'):
        if value is None:
            prepared(inputs)
        else:
            value.verify_fresh(inputs[1], inputs[2], 'synthetic context')


def test_materialized_mutation_does_not_change_private_preparation_or_repeat_result(inputs):
    value = prepared(inputs)
    args = ('a' * 32, None, 'b' * 32, '2026-11-08T00:00:00Z')
    resources, manifest, raw = value.materialize(*args)
    expected = deepcopy((resources, manifest, raw))
    next(item for item in resources if item['kind'] == 'hash')['fields']['name'] = 'changed output'
    next(item for item in resources if item['kind'] == 'set')['members'].append('changed output')
    manifest['counts']['curated'] = 100
    assert value.materialize(*args) == expected
    value.verify_fresh(inputs[1], inputs[2], 'synthetic context')


def test_materialized_generation_and_previous_bind_derived_keys_and_byte_ledger(inputs):
    value = prepared(inputs)
    first_resources, first, first_raw = value.materialize(
        'a' * 32, None, 'b' * 32, '2026-11-08T00:00:00Z')
    second_resources, second, second_raw = value.materialize(
        'c' * 32, 'a' * 32, 'd' * 32, '2026-11-08T00:00:00Z')
    assert {item['key'].replace('a' * 32, 'c' * 32) for item in first_resources} == {
        item['key'] for item in second_resources}
    assert second['previous'] == first['generation']
    assert second['source_digest'] == first['source_digest']
    assert second['context_digest'] == first['context_digest']
    assert second['projection_bytes'] - first['projection_bytes'] == len(second_raw) - len(first_raw) == 30
