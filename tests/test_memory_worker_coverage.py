"""Retain rejected offline proposals and stop when authority changes between stages."""

from copy import deepcopy

import pytest

from attune_harness.memory_worker import InjectedParticipant, WorkerStore, run, validated_proposal
from test_memory_worker import packet, proposal  # noqa: F401


def test_invalid_sample_audit_quarantines_proposal_and_retains_exact_reply(tmp_path, packet):
    envelope, policy = packet
    policy.update(sample_modulus=1, sample_bucket=0)
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    calls = []
    invalid_audit = dict(verdict='supported', reason='Invented evidence', evidence_ids=['absent'])

    def callback(role, profile, prompt, schema):
        calls.append(role)
        return {'value': invalid_audit if role == 'audit' else proposal(envelope)}

    result = run(store, 'job', InjectedParticipant(callback, ['luna', 'astra']))
    assert calls == ['worker', 'audit']
    assert result['status'] == 'quarantined'
    assert result['result']['audit']['state'] == 'rejected'
    assert result['attempts'][-1]['reply']['value'] == invalid_audit
    with pytest.raises(ValueError, match='applicable proposal'):
        validated_proposal(store, 'job')
    assert store.read()['envelope'] == envelope


def test_rejected_proposals_are_retained_after_bounded_escalation(tmp_path, packet):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    replies = [{'mistake': 'first'}, {'mistake': 'second'}]
    calls = []

    def callback(role, profile, prompt, schema):
        calls.append((role, profile))
        return {'value': replies[len(calls) - 1]}

    result = run(store, 'job', InjectedParticipant(callback, ['luna', 'astra']))
    assert calls == [('worker', 'luna'), ('escalation', 'astra')]
    assert result['status'] == 'rejected'
    assert [a['reply']['value'] for a in result['attempts']] == replies
    assert result['result']['first']['accepted'] is False
    assert result['result']['final']['accepted'] is False
    retained = store.read()
    with pytest.raises(ValueError, match='already claimed'):
        run(store, 'job', InjectedParticipant(callback, ['luna', 'astra']))
    assert store.read() == retained


@pytest.mark.parametrize('change', ['host_authority', 'participant_profiles'])
def test_changed_authority_stops_escalation_before_second_dispatch(tmp_path, packet, change):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    calls, authorizations = [], []

    def callback(role, profile, prompt, schema):
        calls.append(role)
        if change == 'participant_profiles':
            actor.profiles = ('luna',)
        return {'value': proposal(envelope, outcome='needs_reasoning')}

    def authorize(job):
        authorizations.append(deepcopy(job))
        if change == 'host_authority' and calls:
            raise ValueError('Host access was revoked')

    actor = InjectedParticipant(callback, ['luna', 'astra'])
    result = run(store, 'job', actor, authorize_job=authorize)
    assert calls == ['worker']
    assert result['status'] == 'stale_stop'
    assert len(result['attempts']) == 1
    assert result['attempts'][0]['state'] == 'completed'
    assert result['attempts'][0]['reply']['value']['outcome'] == 'needs_reasoning'
    assert len(authorizations) == 2
    with pytest.raises(ValueError, match='applicable proposal'):
        validated_proposal(store, 'job')


def test_missing_participant_profile_never_claims_or_dispatches(tmp_path, packet):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)

    def forbidden(*args):
        pytest.fail('Participant missing an authorized profile must not be called')

    with pytest.raises(ValueError, match='authorized profiles'):
        run(store, 'job', InjectedParticipant(forbidden, ['luna']))
    assert store.read()['jobs'] == {}


def test_participant_exception_retains_transport_evidence_without_retry(tmp_path, packet):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    calls = []
    evidence = dict(stage='offline_fixture', response_received=False)

    def callback(*args):
        calls.append(args[0])
        error = TimeoutError('offline reply lost')
        error.evidence = evidence
        raise error

    actor = InjectedParticipant(callback, ['luna', 'astra'])
    with pytest.raises(TimeoutError):
        run(store, 'job', actor)
    evidence['response_received'] = True
    retained = store.inspect('job')
    assert retained['status'] == 'unresolved'
    assert retained['attempts'][0]['transport_evidence']['response_received'] is False
    with pytest.raises(ValueError, match='already claimed'):
        run(store, 'job', actor)
    assert calls == ['worker']
    assert store.inspect('job') == retained
