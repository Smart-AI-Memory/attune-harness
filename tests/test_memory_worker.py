"""Behavioral boundaries for the shared proposal worker, with no native calls."""

from copy import deepcopy
import multiprocessing
from pathlib import Path

import pytest

from attune_harness import memory_contract as contract
from attune_harness.memory_worker import InjectedParticipant, WorkerStore, run, sampled, validated_proposal
from attune_harness.review_store import PersistenceError


@pytest.fixture
def packet():
    fact = dict(id='f1', text='Use port 9000 except in CI.', scope='project', kind='note', source_ids=['s1'])
    sources = [dict(id='s1', text=fact['text'], scope='project', context='Original decision', owner='patrick', classification='internal'),
               dict(id='s2', text='Correction: use port 9001 except in CI.', scope='project', context='Authorized correction', owner='patrick', classification='internal')]
    envelope = dict(schema_version=1, capability=contract.CAPABILITY, task_class='routine',
                    input=dict(task='Correct the port while retaining the CI exception.', record=dict(version=7, facts=[fact]), sources=sources,
                               grants=dict(scopes=['project'], kinds=['note', 'decision'], create_ids=['f2'], remove_ids=['f1'], classify_ids=['f1'])),
                    access=dict(actor='patrick', owners=['patrick'], classifications=['internal'], profiles=['luna', 'astra']))
    policy = dict(sample_modulus=10000, sample_bucket=0, sample_salt='host-salt', routine_profile='luna', stronger_profile='astra')
    while sampled('job', policy):
        policy['sample_salt'] += 'x'
    return envelope, policy


def proposal(envelope, *, outcome='update'):
    facts = deepcopy(envelope['input']['record']['facts'])
    facts[0].update(text='Use port 9001 except in CI.', source_ids=['s1', 's2'])
    return dict(operation='amend', outcome=outcome, facts=facts if outcome == 'update' else [],
                reason='The correction preserves the CI exception.', evidence_ids=['s2'],
                request='Please supply the missing decision.' if outcome.startswith('needs_') else '')


def participant(envelope, calls, *, outcome='update', audit='supported', on_call=None):
    def callback(role, profile, prompt, schema):
        calls.append((role, profile))
        if on_call:
            on_call(role, prompt)
        value = (dict(verdict=audit, reason='Checked the correction and exception.', evidence_ids=['s1', 's2'])
                 if role == 'audit' else proposal(envelope, outcome=outcome))
        return {'value': value}
    return InjectedParticipant(callback, ['luna', 'astra'])


def test_routine_success_does_not_repeat_on_stronger(tmp_path, packet):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    calls = []
    result = run(store, 'job', participant(envelope, calls))
    assert calls == [('worker', 'luna')]
    assert result['status'] == 'proposal_ready'
    assert validated_proposal(store, 'job')['version'] == 8
    assert store.read()['envelope'] == envelope  # Proposals have no memory effect.


def test_known_difficult_direct_to_stronger(tmp_path, packet):
    envelope, policy = packet
    envelope['task_class'] = 'known_difficult'
    calls = []
    result = run(WorkerStore.create(tmp_path / 'jobs', envelope, policy), 'job', participant(envelope, calls))
    assert result['status'] == 'proposal_ready'
    assert calls == [('worker', 'astra')]


@pytest.mark.parametrize(('outcome', 'expected', 'count'), [('needs_reasoning', 'unresolved_reasoning', 2),
                                                         ('needs_evidence', 'await_evidence', 1),
                                                         ('needs_decision', 'await_decision', 1),
                                                         ('no_change', 'complete_no_change', 1)])
def test_disposition_routes(tmp_path, packet, outcome, expected, count):
    envelope, policy = packet
    calls = []
    result = run(WorkerStore.create(tmp_path / 'jobs', envelope, policy), 'job', participant(envelope, calls, outcome=outcome))
    assert result['status'] == expected
    assert len(calls) == count


@pytest.mark.parametrize('audit', ['supported', 'unsupported', 'uncertain'])
def test_sampled_semantic_audit(tmp_path, packet, audit):
    envelope, policy = packet
    policy.update(sample_modulus=1, sample_bucket=0)
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    calls = []
    result = run(store, 'job', participant(envelope, calls, audit=audit))
    assert calls == [('worker', 'luna'), ('audit', 'astra')]
    assert result['status'] == ('proposal_ready' if audit == 'supported' else 'quarantined')
    if audit != 'supported':
        with pytest.raises(ValueError):
            validated_proposal(store, 'job')


def test_invalid_routine_output_escalates_once_then_sample(tmp_path, packet):
    envelope, policy = packet
    policy.update(sample_modulus=1, sample_bucket=0)
    calls = []
    def callback(role, profile, prompt, schema):
        calls.append((role, profile))
        if role == 'worker':
            return {'value': {'invalid': 'answer'}}
        if role == 'audit':
            return {'value': dict(verdict='supported', reason='Source supported.', evidence_ids=['s2'])}
        assert prompt['previous_attempt']['accepted'] is False
        return {'value': proposal(envelope)}
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    result = run(store, 'job', InjectedParticipant(callback, ['luna', 'astra']))
    assert result['status'] == 'proposal_ready'
    assert calls == [('worker', 'luna'), ('escalation', 'astra'), ('audit', 'astra')]
    assert validated_proposal(store, 'job')['facts'][0]['text'] == 'Use port 9001 except in CI.'


def test_stronger_reasoning_handoff_can_produce_valid_proposal(tmp_path, packet):
    envelope, policy = packet
    calls = []
    def callback(role, profile, prompt, schema):
        calls.append((role, profile))
        return {'value': proposal(envelope, outcome='needs_reasoning' if role == 'worker' else 'update')}
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    run(store, 'job', InjectedParticipant(callback, ['luna', 'astra']))
    assert validated_proposal(store, 'job')['version'] == 8
    assert calls == [('worker', 'luna'), ('escalation', 'astra')]


@pytest.mark.parametrize('outcome', ['no_change', 'needs_evidence', 'needs_decision'])
def test_sample_review_covers_non_updates(tmp_path, packet, outcome):
    envelope, policy = packet
    policy.update(sample_modulus=1, sample_bucket=0)
    calls = []
    result = run(WorkerStore.create(tmp_path / 'jobs', envelope, policy), 'job',
                 participant(envelope, calls, outcome=outcome, audit='unsupported'))
    assert result['status'] == 'quarantined'
    assert calls == [('worker', 'luna'), ('audit', 'astra')]


@pytest.mark.parametrize('change', ['owner', 'classification', 'scope', 'profile', 'kind', 'boolean_version', 'duplicate_source'])
def test_invalid_host_input_never_claims_or_dispatches(tmp_path, packet, change):
    envelope, policy = packet
    if change in ('owner', 'classification', 'scope'):
        envelope['input']['sources'][0][change] = 'foreign'
    elif change == 'profile':
        policy['routine_profile'] = 'unapproved'
    elif change == 'kind':
        envelope['input']['record']['facts'][0]['kind'] = 'security_public'
    elif change == 'boolean_version':
        envelope['input']['record']['version'] = True
    else:
        envelope['input']['sources'][1]['id'] = 's1'
    with pytest.raises(ValueError):
        WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    assert not (tmp_path / 'jobs').exists()


@pytest.mark.parametrize('change', ['unknown_evidence', 'empty_evidence', 'duplicate_evidence', 'cross_scope', 'unknown_fact', 'scope_move', 'false_no_change', 'copied_version', 'ungranted_kind'])
def test_invalid_proposals(packet, change):
    envelope, _ = packet
    value = proposal(envelope)
    if change == 'unknown_evidence':
        value['evidence_ids'] = ['missing-attachment.md']
    elif change == 'empty_evidence':
        value['evidence_ids'] = []
    elif change == 'duplicate_evidence':
        value['evidence_ids'] = ['s1', 's1']
    elif change == 'cross_scope':
        envelope['input']['sources'][1]['scope'] = 'foreign'
    elif change == 'unknown_fact':
        value['facts'][0]['id'] = 'foreign'
    elif change == 'scope_move':
        value['facts'][0]['scope'] = 'foreign'
    elif change == 'false_no_change':
        value['outcome'] = 'no_change'
    elif change == 'copied_version':
        value['version'] = 8
    else:
        value['facts'][0]['kind'] = 'security_public'
    with pytest.raises(ValueError):
        contract.normalize(envelope['input'], value)


def test_unchanged_preview_and_long_content_preserved(packet):
    envelope, policy = packet
    text = 'A long procedural memory with important exceptions. ' * 400
    envelope['input']['record']['facts'][0]['text'] = text
    envelope['input']['sources'][0]['text'] = text
    contract.validate(envelope, policy)
    value = proposal(envelope, outcome='no_change')
    value['facts'] = deepcopy(envelope['input']['record']['facts'])
    assert contract.normalize(envelope['input'], value) == envelope['input']['record']
    schema = contract.schema_for(envelope['input'])
    assert schema['properties']['evidence_ids']['items']['enum'] == ['s1', 's2']


@pytest.mark.parametrize('operation', ['capture', 'forget', 'consolidate', 'classify'])
def test_supported_operations(packet, operation):
    envelope, _ = packet
    bound = envelope['input']
    value = proposal(envelope)
    value['operation'] = operation
    value['facts'] = deepcopy(bound['record']['facts'])
    if operation == 'capture':
        value['facts'].append(dict(id='f2', text='Use another port in CI.', scope='project', kind='note', source_ids=['s2']))
    elif operation == 'forget':
        value['facts'] = []
    elif operation == 'consolidate':
        bound['record']['facts'].append(dict(id='f2', text='Use port 9001 except in CI.', scope='project', kind='note', source_ids=['s2']))
        bound['grants']['remove_ids'].append('f2')
        value['facts'][0].update(text='Use port 9001 except in CI.', source_ids=['s1', 's2'])
    else:
        value['facts'][0]['kind'] = 'decision'
    assert contract.normalize(bound, value)['version'] == 8


@pytest.mark.parametrize('shape', ['single_to_empty', 'all_to_empty', 'missing_provenance',
                                 'survivor_drops_own_provenance', 'wrong_kind_target', 'wrong_scope_target'])
def test_consolidation_requires_retained_provenance(packet, shape):
    envelope, _ = packet
    bound = envelope['input']
    value = proposal(envelope)
    value['operation'] = 'consolidate'
    if shape == 'single_to_empty':
        value['facts'] = []
    else:
        bound['record']['facts'].append(dict(id='f2', text='Corrected port is 9001 except in CI.', scope='project', kind='note', source_ids=['s2']))
        bound['grants']['remove_ids'].append('f2')
        if shape == 'all_to_empty':
            value['facts'] = []
        elif shape == 'missing_provenance':
            value['facts'][0]['source_ids'] = ['s1']
        elif shape == 'survivor_drops_own_provenance':
            value['facts'][0]['source_ids'] = ['s2']
        else:
            key = 'kind' if shape == 'wrong_kind_target' else 'scope'
            bound['record']['facts'][1][key] = 'other'
    with pytest.raises(ValueError):
        contract.normalize(bound, value)


@pytest.mark.parametrize('change', ['policy', 'envelope', 'aba'])
def test_stale_change_during_call_stops_publication(tmp_path, packet, change):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    calls = []
    def mutate(role, prompt):
        if change == 'policy':
            updated = {**policy, 'sample_salt': 'new-salt'}
            store.replace_host_state(policy=updated)
        else:
            updated = deepcopy(envelope)
            updated['input']['task'] = 'Changed task'
            store.replace_host_state(envelope=updated)
            if change == 'aba':
                store.replace_host_state(envelope=envelope)
    result = run(store, 'job', participant(envelope, calls, on_call=mutate))
    assert result['status'] == 'stale_stop'
    assert len(calls) == 1
    with pytest.raises(contract.StaleInput):
        validated_proposal(store, 'job')


def test_duplicate_job_and_uncertain_callback_never_retry(tmp_path, packet):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    calls = []
    def fail(*args):
        calls.append(args[0])
        assert store.inspect('job')['attempts'][0]['state'] == 'dispatched'
        raise TimeoutError('response lost')
    actor = InjectedParticipant(fail, ['luna', 'astra'])
    with pytest.raises(TimeoutError):
        run(store, 'job', actor)
    with pytest.raises(ValueError, match='already claimed'):
        run(WorkerStore(tmp_path / 'jobs'), 'job', actor)
    assert store.inspect('job')['status'] == 'unresolved'
    assert calls == ['worker']


@pytest.mark.parametrize('failure_at', [1, 2, 3, 4])
def test_persistence_failures_never_redispatch(tmp_path, packet, monkeypatch, failure_at):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    original = store.records.save
    saves, calls = [], []
    def fail(state):
        saves.append(1)
        if len(saves) == failure_at:
            raise PersistenceError('disk failure')
        original(state)
    monkeypatch.setattr(store.records, 'save', fail)
    with pytest.raises(PersistenceError):
        run(store, 'job', participant(envelope, calls))
    assert len(calls) == (1 if failure_at >= 3 else 0)
    if failure_at > 1:
        with pytest.raises(ValueError, match='already claimed'):
            run(store, 'job', participant(envelope, calls))


def test_native_looking_callback_cannot_bypass_transport_boundary(tmp_path, packet):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    def general_native(*args):
        pytest.fail('Unqualified native adapter dispatched')
    general_native.tools = []
    with pytest.raises(ValueError, match='no-tools'):
        run(store, 'job', general_native)


def test_tampered_candidate_or_sample_cannot_apply(tmp_path, packet):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    run(store, 'job', participant(envelope, []))
    with store.records.lease():
        state = store.read()
        state['jobs']['job']['result']['final']['candidate']['facts'][0]['text'] = 'forged'
        store.records.save(state)
    with pytest.raises(ValueError):
        validated_proposal(store, 'job')


@pytest.mark.parametrize('change', ['response_and_candidate', 'first_and_final', 'audit_response', 'audit_prompt',
                                  'worker_prompt', 'worker_schema', 'worker_profile', 'attempt_state',
                                  'drop_attempt', 'escalation_flag', 'sample_flag'])
def test_coordinated_result_alteration_refused(tmp_path, packet, change):
    envelope, policy = packet
    policy.update(sample_modulus=1, sample_bucket=0)
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    run(store, 'job', participant(envelope, []))
    with store.records.lease():
        state = store.read()
        job = state['jobs']['job']
        result = job['result']
        if change in ('response_and_candidate', 'first_and_final'):
            result['final']['response']['facts'][0]['text'] = 'FORGED BUT STRUCTURALLY VALID'
            result['final']['candidate'] = contract.normalize(envelope['input'], result['final']['response'])
            if change == 'first_and_final':
                result['first'] = deepcopy(result['final'])
        elif change == 'audit_response':
            result['audit']['response']['reason'] = 'A different invented review'
        elif change == 'audit_prompt':
            job['attempts'][-1]['prompt_digest'] = 'other'
        elif change == 'worker_prompt':
            job['attempts'][0]['prompt_digest'] = 'other'
        elif change == 'worker_schema':
            job['attempts'][0]['schema_digest'] = 'other'
        elif change == 'worker_profile':
            job['attempts'][0]['profile'] = 'unapproved'
        elif change == 'attempt_state':
            job['attempts'][0]['state'] = 'dispatched'
        elif change == 'drop_attempt':
            job['attempts'].pop()
        elif change == 'escalation_flag':
            result['escalated'] = True
        else:
            job['sampled'] = False
        store.records.save(state)
    with pytest.raises(ValueError):
        validated_proposal(store, 'job')


def _claim_in_child(directory, queue):
    try:
        WorkerStore(directory).claim('job', InjectedParticipant(None, ['luna', 'astra']))
        queue.put('claimed')
    except (ValueError, PersistenceError):
        queue.put('refused')


def test_process_claim_exclusion(tmp_path, packet):
    envelope, policy = packet
    store = WorkerStore.create(tmp_path / 'jobs', envelope, policy)
    ctx = multiprocessing.get_context('spawn')
    queue = ctx.Queue()
    children = [ctx.Process(target=_claim_in_child, args=(str(store.records.directory), queue)) for _ in range(2)]
    for child in children:
        child.start()
    results = [queue.get(timeout=15) for _ in children]
    for child in children:
        child.join(timeout=15)
        assert child.exitcode == 0
    assert sorted(results) == ['claimed', 'refused']
