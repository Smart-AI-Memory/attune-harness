"""Funding is bound explicitly and cannot silently dispatch through legacy auth."""
# qualify: platform

import copy
from threading import Event

import pytest

from attune_harness import consultation, consultation_preflight
from attune_harness.features import FeatureUnavailable
from attune_harness.native import NativeExchange
from attune_harness.participant_funding import validate
from attune_harness.review import authorize_external
from attune_harness.review_contract import accept_request, load_registry, validate_registry
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import checkpoint_digest
from attune_harness.task_contract import accept_task, check_fresh
from attune_harness.task_policies import execute_task
from attune_harness.work_contract import check_work_fresh

from test_review import case, change, change_config
from test_task_contract import draft as task_draft, response as task_response
from test_work_contract import work, make as make_work, accept as accept_work


POLICIES = [
    ('claude', {'mode': 'subscription'}),
    ('codex', {'mode': 'subscription'}),
    ('codex', {'mode': 'api', 'credential_env': 'OPENAI_API_KEY'}),
]


def configuration(adapter, policy):
    return {'schema_version': 1, 'question': 'Inspect the frozen source',
            'author': {'provider': 'chair', 'model': 'chair-fixture'}, 'rounds': 1,
            'participants': {'peer': {'adapter': adapter, 'timeout': 10,
                'identity': {'provider': adapter, 'model': 'explicit-fixture'},
                'funding': copy.deepcopy(policy)}}}


def registry(adapter, policy):
    return {'schema_version': 1, 'participants': {
        'peer': {'adapter': adapter, 'model': 'explicit-fixture', 'timeout': 10,
                 'tools': [], 'max_turns': 1, 'max_tool_calls': 0, 'funding': copy.deepcopy(policy)},
        'demo': {'adapter': 'deterministic', 'tools': [], 'max_turns': 1, 'max_tool_calls': 0}}}


@pytest.mark.parametrize('adapter,policy', POLICIES)
def test_both_formats_retain_explicit_funding_without_normalizing(tmp_path, adapter, policy):
    value = registry(adapter, policy)
    before = copy.deepcopy(value)
    assert validate_registry(value, tmp_path / 'registry.json') is value
    assert value == before
    config = configuration(adapter, policy)
    original = copy.deepcopy(config)
    assert consultation.configuration(config, 'source-review') is config
    assert config == original
    # An omitted legacy field remains omitted, rather than acquiring a default.
    del value['participants']['peer']['funding']
    original = copy.deepcopy(value)
    assert validate_registry(value, tmp_path / 'registry.json') == original
    assert 'funding' not in value['participants']['peer']
    del config['participants']['peer']['funding']
    original = copy.deepcopy(config)
    assert consultation.configuration(config, 'source-review') == original
    assert 'funding' not in config['participants']['peer']


@pytest.mark.parametrize('policy', [
    None, {}, True, {'mode': 'automatic'}, {'mode': 'api'},
    {'mode': 'api', 'credential_env': ''},
    {'mode': 'api', 'credential_env': '/secret/file'},
    {'mode': 'api', 'credential_env': '$(cat secret)'},
    {'mode': 'api', 'credential_env': 'sk-secret-sentinel'},
    {'mode': 'api', 'credential_env': True},
    {'mode': 'api', 'credential_env': 'A' * 129},
    {'mode': 'api', 'credential_env': 'OPENAI_API_KEY', 'key': 'secret-sentinel'},
    {'mode': 'subscription', 'credential_env': 'secret-sentinel'},
])
def test_invalid_policy_refuses_in_both_owners_without_echo(tmp_path, policy):
    for owner, value in ((lambda value: validate_registry(value, tmp_path / 'registry.json'),
                          registry('codex', policy)),
                         (lambda value: consultation.configuration(value, 'source-review'),
                          configuration('codex', policy))):
        with pytest.raises(ValueError) as error:
            owner(value)
        assert 'secret-sentinel' not in str(error.value)


@pytest.mark.parametrize('adapter', ['deterministic', 'command', 'antigravity'])
def test_nonnative_policy_is_not_a_silent_noop(adapter):
    with pytest.raises(ValueError, match='only for native'):
        validate(adapter, {'mode': 'subscription'})


def test_claude_api_is_outside_the_selected_scope():
    with pytest.raises(ValueError, match='only for Codex'):
        validate('claude', {'mode': 'api', 'credential_env': 'ANTHROPIC_API_KEY'})


@pytest.mark.parametrize('adapter,policy', POLICIES)
def test_preflight_refuses_before_any_version_or_status_probe(monkeypatch, adapter, policy):
    def forbidden(*args, **kwargs):
        pytest.fail('unqualified funding reached a CLI probe')
    monkeypatch.setattr(consultation_preflight, '_probe', forbidden)
    with pytest.raises(FeatureUnavailable, match='not admitted'):
        consultation_preflight.preflight(configuration(adapter, policy))


@pytest.mark.parametrize('adapter,policy', POLICIES)
def test_owner_refuses_before_journal_dispatch(tmp_path, adapter, policy):
    root = tmp_path.resolve() / 'repo'
    root.mkdir()
    (root / 'sample.py').write_text('x = 1\n', encoding='utf-8')
    directory = tmp_path.resolve() / 'run'
    record = consultation.prepare('source-review', root, ['sample.py'],
                                  configuration(adapter, policy), directory)
    before = (directory / 'record.json').read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail('unqualified funding reached dispatch')
    with pytest.raises(FeatureUnavailable, match='not admitted'):
        consultation.run(directory, record['contract_digest'], allow_external=True,
                         allow_native=True, dispatcher=forbidden)
    assert (directory / 'record.json').read_bytes() == before
    assert consultation.load(directory)['events'] == []
    assert consultation.load(directory)['status'] == 'prepared'


@pytest.mark.parametrize('adapter,policy', POLICIES)
def test_direct_paths_cannot_bypass_the_funding_guard(tmp_path, adapter, policy):
    seat = configuration(adapter, policy)['participants']['peer']
    with pytest.raises(FeatureUnavailable, match='not admitted'):
        consultation.dispatch(seat, {}, tmp_path, Event())
    with pytest.raises(FeatureUnavailable, match='not admitted'):
        ReviewExchange(registry(adapter, policy)['participants']['peer'], tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail('unqualified funding reached native runner')
    with pytest.raises(FeatureUnavailable, match='not admitted'):
        NativeExchange(adapter, cwd=tmp_path, funding=policy, runner=forbidden)


def test_explicit_null_is_not_legacy_authentication(tmp_path):
    with pytest.raises(ValueError, match='Funding requires'):
        NativeExchange('codex', cwd=tmp_path, funding=None)


def test_only_selected_participants_block_dispatch():
    value = registry('codex', {'mode': 'subscription'})['participants']
    # Unused native entries in a registry do not block a selected demo policy.
    authorize_external({'lead': value['demo']}, False)
    with pytest.raises(FeatureUnavailable, match='not admitted'):
        authorize_external({'lead': value['peer']}, True)


@pytest.mark.parametrize('policy', [
    {'mode': 'subscription'}, {'mode': 'api', 'credential_env': 'OTHER_API_KEY'}])
def test_funding_changes_require_new_contract_acceptance(tmp_path, policy):
    root = tmp_path.resolve() / 'repo'
    root.mkdir()
    (root / 'sample.py').write_text('x = 1\n', encoding='utf-8')
    directory = tmp_path.resolve() / 'run'
    record = consultation.prepare('source-review', root, ['sample.py'],
        configuration('codex', {'mode': 'api', 'credential_env': 'OPENAI_API_KEY'}), directory)
    record['contract']['configuration']['participants']['peer']['funding'] = policy
    # Even a recomputed outer checkpoint cannot reuse the accepted contract.
    record['checkpoint_digest'] = checkpoint_digest(record)
    with pytest.raises(ValueError, match='Changed consultation contract'):
        consultation.validate_record(record, directory)


def test_mutated_exchange_configuration_cannot_drop_into_legacy_dispatch(tmp_path):
    seat = registry('codex', {'mode': 'subscription'})['participants']['peer']
    del seat['funding']
    exchange = ReviewExchange(seat, tmp_path)
    seat['funding'] = {'mode': 'subscription'}
    with pytest.raises(FeatureUnavailable, match='not admitted'):
        exchange('{}')


def test_funding_does_not_create_independent_model_identities():
    value = configuration('codex', {'mode': 'subscription'})
    value['participants']['other'] = copy.deepcopy(value['participants']['peer'])
    value['participants']['other']['funding'] = {'mode': 'api', 'credential_env': 'OPENAI_API_KEY'}
    with pytest.raises(ValueError, match='distinct configured'):
        consultation.configuration(value, 'roundtable')


INITIAL_API = {'mode': 'api', 'credential_env': 'OPENAI_API_KEY'}
CHANGED_FUNDING = [{'mode': 'subscription'}, {'mode': 'api', 'credential_env': 'OTHER_API_KEY'}]


def funded_codex(value, name):
    value['participants'][name].update(adapter='codex', model='explicit-fixture',
                                      timeout=10, funding=copy.deepcopy(INITIAL_API))


@pytest.mark.parametrize('policy', CHANGED_FUNDING)
def test_funding_only_registry_change_invalidates_review_form(case, policy):
    change_config(case, lambda value: funded_codex(value, 'alpha'))
    assert accept_request(case[0], load_registry(case[1]))['submission']['accepted'] is True
    change(case[1], lambda value: value['participants']['alpha'].update(funding=copy.deepcopy(policy)))
    with pytest.raises(ValueError, match='Stale form revision'):
        accept_request(case[0], load_registry(case[1]))


@pytest.mark.parametrize('policy', CHANGED_FUNDING)
def test_funded_task_refuses_factory_and_funding_change_is_stale(case, policy):
    change(case[1], lambda value: funded_codex(value, 'alpha'))
    task_draft(case)
    submission = task_response(case[2])
    submission['permissions']['external'] = True
    accepted = accept_task(case[2], submission)
    assert accepted['bindings']['assessment']['assignments']['assessor']['configuration']['funding'] == INITIAL_API
    before = (case[2] / 'record.json').read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail('unqualified funding reached the exchange factory')
    with pytest.raises(FeatureUnavailable, match='not admitted'):
        execute_task(case[2], exchange_factory=forbidden)
    assert (case[2] / 'record.json').read_bytes() == before
    change(case[1], lambda value: value['participants']['alpha'].update(funding=copy.deepcopy(policy)))
    with pytest.raises(ValueError, match='Stale registry'):
        check_fresh(accepted)


@pytest.mark.parametrize('policy', CHANGED_FUNDING)
def test_funding_only_registry_change_invalidates_accepted_work(work, policy):
    change(work[1], lambda value: funded_codex(value, 'local'))
    accepted = accept_work(work, make_work(work))
    before = (work[2]['directory'] / 'record.json').read_bytes()
    change(work[1], lambda value: value['participants']['local'].update(funding=copy.deepcopy(policy)))
    with pytest.raises(ValueError, match='Stale work evidence'):
        check_work_fresh(accepted)
    assert (work[2]['directory'] / 'record.json').read_bytes() == before
