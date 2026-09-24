"""Offline host authority and replay receipts with real, isolated native roots."""

from copy import deepcopy
import os
from pathlib import Path

import pytest

from attune_harness.memory_context import MemoryHost
from attune_harness.memory_worker import WorkerStore
from attune_harness.review_contract import digest
from test_memory_reader import config_for, seed_raw
from test_memory_worker import packet, proposal  # noqa: F401


@pytest.fixture
def host(tmp_path):
    root = tmp_path / 'memories'
    seed_raw(root)
    config = config_for(('raw', root, 'raw', 'project-a'))
    config.update(profiles=['luna', 'astra'], scopes=['project-a', 'global', 'project'])
    jobs = tmp_path / 'jobs'
    jobs.mkdir()
    return MemoryHost(config, jobs=jobs)


def create(host, packet):
    envelope, policy = packet
    assert host.invoke('create', dict(run_id='run', envelope=envelope, policy=policy)) == dict(
        status='created', mode='offline_replay', generation=0)
    return WorkerStore(host.jobs / 'run')


def reply(envelope, role='worker', profile='luna', outcome='update'):
    return dict(role=role, profile=profile, value=proposal(envelope, outcome=outcome))


def test_replay_persists_proposal_without_memory_effect_or_duplicate_work(host, packet):
    store = create(host, packet)
    source = host.adapter.config['roots'][0]['path']
    source = Path(source) / 'findings.jsonl'
    before = source.read_bytes()
    args = dict(run_id='run', job_id='job', replies=[reply(packet[0]), reply(packet[0])])
    result = host.invoke('replay', args)
    assert result['status'] == 'proposal_ready'
    assert result['provider_calls'] == 0 and result['unused_reply_count'] == 1
    assert len(result['result']['attempts']) == 1
    assert result['result'] == host.invoke('inspect', dict(run_id='run', job_id='job'))
    retained = store.read()
    result['result']['result']['final']['candidate']['facts'][0]['text'] = 'caller mutation'
    assert store.read() == retained
    with pytest.raises(ValueError, match='already claimed'):
        host.invoke('replay', args)
    assert store.read() == retained
    assert source.read_bytes() == before


@pytest.mark.parametrize(('outcome', 'status', 'roles'), [
    ('needs_evidence', 'await_evidence', [('worker', 'luna')]),
    ('needs_reasoning', 'proposal_ready', [('worker', 'luna'), ('escalation', 'astra')]),
])
def test_replay_host_routes_missing_evidence_separately_from_reasoning(host, packet, outcome, status, roles):
    create(host, packet)
    result = host.invoke('replay', dict(run_id='run', job_id='job', replies=[
        reply(packet[0], outcome=outcome), reply(packet[0], 'escalation', 'astra')]))
    assert result['status'] == status
    assert [(a['role'], a['profile']) for a in result['result']['attempts']] == roles
    assert result['unused_reply_count'] == 2 - len(roles)
    assert result['result']['result']['first']['response']['outcome'] == outcome


@pytest.mark.parametrize('failure', ['wrong_route', 'missing_escalation'])
def test_bad_replay_retains_failed_attempt_and_cannot_resume(host, packet, failure):
    store = create(host, packet)
    replies = [reply(packet[0], profile='astra')] if failure == 'wrong_route' else [
        reply(packet[0], outcome='needs_reasoning')]
    args = dict(run_id='run', job_id='job', replies=replies)
    with pytest.raises(ValueError, match='Replay'):
        host.invoke('replay', args)
    job = store.inspect('job')
    assert job['status'] == 'unresolved'
    assert job['attempts'][-1]['state'] == 'unresolved'
    assert job['attempts'][-1]['error'] == 'ValueError'
    assert len(job['attempts']) == (1 if failure == 'wrong_route' else 2)
    with pytest.raises(ValueError, match='already claimed'):
        host.invoke('replay', args)
    assert store.inspect('job') == job


@pytest.mark.parametrize('dimension', ['actor', 'owners', 'classifications', 'profiles', 'scopes'])
def test_worker_authority_cannot_expand_host_grants(host, packet, dimension):
    envelope, policy = deepcopy(packet)
    if dimension == 'actor':
        envelope['access']['actor'] = 'other'
    elif dimension == 'scopes':
        envelope['input']['grants']['scopes'].append('other')
    else:
        envelope['access'][dimension].append('public' if dimension == 'classifications' else 'other')
    with pytest.raises(ValueError, match='host authority'):
        host.invoke('create', dict(run_id='refused', envelope=envelope, policy=policy))
    assert not (host.jobs / 'refused').exists()


def test_inspection_rechecks_historical_job_authority_after_current_state_is_narrowed(host, packet):
    envelope, policy = deepcopy(packet)
    envelope['access']['owners'].append('previous-owner')
    store = WorkerStore.create(host.jobs / 'run', envelope, policy)
    from attune_harness.memory_worker import InjectedParticipant
    store.claim('old-job', InjectedParticipant(None, ['luna', 'astra']))
    store.replace_host_state(envelope=packet[0])
    retained = store.read()
    with pytest.raises(ValueError, match='host authority'):
        host.invoke('inspect', dict(run_id='run', job_id='old-job'))
    assert store.read() == retained


@pytest.mark.parametrize('run_id', ['../escape', '/absolute', '', 'x' * 65])
def test_run_identity_refuses_escape_before_creating_files(host, packet, run_id):
    with pytest.raises(ValueError, match='Invalid run identity'):
        host.invoke('create', dict(run_id=run_id, envelope=packet[0], policy=packet[1]))
    assert list(host.jobs.iterdir()) == []


@pytest.mark.skipif(os.name != 'posix', reason='symlink setup requires POSIX')
def test_symlinked_run_and_replaced_jobs_root_are_refused(host, packet, tmp_path):
    external = tmp_path / 'external'
    external.mkdir()
    (host.jobs / 'escape').symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match='escape its authorized root'):
        host.invoke('create', dict(run_id='escape', envelope=packet[0], policy=packet[1]))
    moved = tmp_path / 'retained-jobs'
    host.jobs.rename(moved)
    host.jobs.symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match='Job directory changed'):
        host.invoke('create', dict(run_id='run', envelope=packet[0], policy=packet[1]))
    assert list(external.iterdir()) == []


def test_job_storage_must_be_canonical_separate_and_explicit(host, packet, tmp_path):
    for directory in (tmp_path, host.adapter.config['roots'][0]['path']):
        with pytest.raises(ValueError, match='separate from every memory root'):
            MemoryHost(host.config, jobs=directory)
    with pytest.raises(ValueError, match='canonical absolute directory'):
        MemoryHost(host.config, jobs=tmp_path / 'missing')
    no_jobs = MemoryHost(host.config)
    with pytest.raises(ValueError, match='no authorized job directory'):
        create(no_jobs, packet)
    unavailable = no_jobs.invoke('execute', dict(run_id='run', job_id='job'))
    assert unavailable['status'] == 'unavailable'
    assert unavailable['dispatch_attempts'] == 0 and unavailable['provider_transmission'] == 'none'


@pytest.mark.skipif(os.name != 'posix', reason='native source reads are POSIX-only')
def test_refresh_replaces_bounded_context_and_invalidates_changed_handles(host):
    packet = host.invoke('recall', dict(query='Aurora', k=2, max_chars=8))
    assert sum(len(i['excerpt']) for i in packet['items']) == 8
    assert all(i['truncated'] for i in packet['items'])
    assert len(host.invoke('resolve', dict(handle=packet['items'][0]['handle']))['text']) > 8
    root = host.adapter.config['roots'][0]['path']
    seed_raw(Path(root), rows=[dict(id='replacement', text='Aurora corrected', type='note', cwd='project-a')])
    refreshed = host.invoke('refresh', dict(context=packet))
    assert refreshed['invalidated_ids'] == [i['handle']['id'] for i in packet['items']]
    assert refreshed['replaces'] == digest(packet)
    assert [i['handle']['id'] for i in refreshed['context']['items']] == ['raw:replacement']


@pytest.mark.parametrize('change', ['authority', 'operation', 'items'])
def test_refresh_refuses_foreign_or_malformed_packet(host, change):
    previous = host.context('Aurora')
    previous[change] = None if change == 'items' else 'foreign'
    with pytest.raises(ValueError):
        host.invoke('refresh', dict(context=previous))


@pytest.mark.parametrize('replies', [[], [None], [{ 'role': 'worker'}], [None] * 4])
def test_malformed_replay_does_not_claim_job(host, packet, replies):
    store = create(host, packet)
    with pytest.raises(ValueError):
        host.invoke('replay', dict(run_id='run', job_id='job', replies=replies))
    assert store.read()['jobs'] == {}


def test_invalid_context_budget_and_mutation_request_leave_sources_unchanged(host):
    source = Path(host.config['roots'][0]['path']) / 'findings.jsonl'
    before = source.read_bytes()
    with pytest.raises(ValueError, match='Context budget'):
        host.invoke('recall', dict(query='Aurora', k=2, max_chars=0))
    with pytest.raises(ValueError, match='memory mutations are unavailable'):
        host.invoke('forget', dict(id='raw:N1'))
    assert source.read_bytes() == before
    assert list(host.jobs.iterdir()) == []
