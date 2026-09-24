"""Reopened offline journals must justify applicable proposals without new dispatch."""

from copy import deepcopy

import pytest

from attune_harness.memory_worker import InjectedParticipant, WorkerStore, run, validated_proposal
from test_memory_worker import packet, proposal  # noqa: F401


def completed_store(tmp_path, packet, *, audit=None, escalate=False):
    envelope, policy = deepcopy(packet)
    if audit is not None:
        policy.update(sample_modulus=1, sample_bucket=0)
    calls = []

    def callback(role, profile, prompt, schema):
        calls.append((role, profile))
        if role == 'audit':
            return {'value': dict(verdict=audit, reason='Checked source support.', evidence_ids=['s2'])}
        outcome = 'needs_reasoning' if escalate and role == 'worker' else 'update'
        return {'value': proposal(envelope, outcome=outcome)}

    actor = InjectedParticipant(callback, ['luna', 'astra'])
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    job = run(store, 'job', actor)
    assert job['status'] == ('quarantined' if audit == 'unsupported' else 'proposal_ready')
    if job['status'] == 'proposal_ready':
        assert validated_proposal(store, 'job')['version'] == 8
    else:
        with pytest.raises(ValueError, match='applicable proposal'):
            validated_proposal(store, 'job')
    return store, actor, calls


def alter_job(store, change):
    with store.records.lease():
        state = store.read()
        change(state['jobs']['job'])
        store.records.save(state)


def assert_refused_without_effects(store, actor, calls, message):
    before = store.records.path.read_bytes()
    dispatched = list(calls)
    reopened = WorkerStore(store.records.directory)
    with pytest.raises(ValueError, match=message):
        validated_proposal(reopened, 'job')
    assert reopened.records.path.read_bytes() == before
    with pytest.raises(ValueError, match='already claimed'):
        run(reopened, 'job', actor)
    assert calls == dispatched
    assert reopened.records.path.read_bytes() == before


def test_missing_sampled_audit_cannot_publish_retained_candidate(tmp_path, packet):
    store, actor, calls = completed_store(tmp_path, packet, audit='supported')
    assert calls == [('worker', 'luna'), ('audit', 'astra')]
    alter_job(store, lambda job: job['result'].update(audit=None))
    assert_refused_without_effects(store, actor, calls, 'Required audit is missing')


def test_unsupported_audit_cannot_be_overridden_by_ready_status(tmp_path, packet):
    store, actor, calls = completed_store(tmp_path, packet, audit='unsupported')
    retained_attempts = deepcopy(store.inspect('job')['attempts'])
    alter_job(store, lambda job: job.update(status='proposal_ready'))
    assert_refused_without_effects(store, actor, calls, 'Semantic review did not support')
    assert store.inspect('job')['attempts'] == retained_attempts


def test_removing_audit_and_attempt_cannot_change_deterministic_sampling(tmp_path, packet):
    store, actor, calls = completed_store(tmp_path, packet, audit='supported')

    def remove_review(job):
        job['sampled'] = False
        job['result']['audit'] = None
        job['attempts'] = job['attempts'][:1]

    alter_job(store, remove_review)
    assert_refused_without_effects(store, actor, calls, 'Sample assignment was altered')


@pytest.mark.parametrize('route', ['initial', 'final'])
def test_saved_route_summary_must_match_policy_and_completed_attempts(tmp_path, packet, route):
    store, actor, calls = completed_store(tmp_path, packet)

    def change_route(job):
        if route == 'initial':
            job['initial_profile'] = 'astra'
        else:
            job['result']['final_profile'] = 'astra'

    alter_job(store, change_route)
    assert_refused_without_effects(store, actor, calls, f'Altered {route} (route|profile)')


@pytest.mark.parametrize('assessment', ['first', 'final'])
def test_saved_acceptance_cannot_disagree_with_retained_response(tmp_path, packet, assessment):
    store, actor, calls = completed_store(tmp_path, packet)
    alter_job(store, lambda job: job['result'][assessment].update(accepted=False))
    message = 'Altered initial assessment' if assessment == 'first' else 'Unaccepted result'
    assert_refused_without_effects(store, actor, calls, message)


def test_escalation_candidate_must_match_the_completed_response(tmp_path, packet):
    store, actor, calls = completed_store(tmp_path, packet, escalate=True)
    assert calls == [('worker', 'luna'), ('escalation', 'astra')]
    retained_reply = deepcopy(store.inspect('job')['attempts'][-1]['reply'])

    def change_candidate(job):
        job['result']['final']['candidate']['facts'][0]['text'] = 'Unreviewed replacement'

    alter_job(store, change_candidate)
    assert_refused_without_effects(store, actor, calls, 'Persisted proposal was altered')
    assert store.inspect('job')['attempts'][-1]['reply'] == retained_reply


def test_saved_offline_transport_cannot_gain_tools(tmp_path, packet):
    store, actor, calls = completed_store(tmp_path, packet)
    alter_job(store, lambda job: job['transport'].update(tools=['write_memory']))
    assert_refused_without_effects(store, actor, calls, 'altered worker transport descriptor')
