"""Durable, bounded proposal worker; storage effects belong to qualified adapters."""

from copy import deepcopy
import hashlib
from pathlib import Path

from . import memory_contract as contract
from .features import FeatureUnavailable
from .review_contract import digest, fields
from .review_store import RunStore, read_record


def sampled(job_id, policy):
    value = (policy['sample_salt'] + ':' + job_id).encode('utf-8')
    return int.from_bytes(hashlib.sha256(value).digest(), 'big') % policy['sample_modulus'] == policy['sample_bucket']


def check_current(state, job):
    if any(state[key] != job[key] for key in ('generation', 'envelope', 'policy')):
        raise contract.StaleInput('Host input, routing, policy or generation changed')


class InjectedParticipant:
    """Trusted host callback for offline integration. This is not a sandbox.

    Native adapters cannot obtain qualification by declaring tools=[]. A future
    native profile needs an independently enforced command and event boundary.
    """

    def __init__(self, callback, profiles):
        self.callback = callback
        self.profiles = tuple(profiles)

    def descriptor(self):
        contract.strings(list(self.profiles), 'injected profiles', nonempty=True)
        return dict(transport='trusted_injected_v1', profiles=list(self.profiles), tools=[])

    def __call__(self, role, profile, prompt, schema):
        return self.callback(role, profile, prompt, schema)


class WorkerStore:
    """Explicit job directory; never discovers or creates a default memory corpus."""

    def __init__(self, directory):
        self.records = RunStore(Path(directory), existing=True)

    @classmethod
    def create(cls, directory, envelope, policy):
        contract.validate(envelope, policy)
        records = RunStore(Path(directory))
        with records.lease():
            records.save(dict(schema_version=1, operation='memory_worker', generation=0,
                              envelope=deepcopy(envelope), policy=deepcopy(policy), jobs={}))
        return cls(directory)

    def read(self):
        state = read_record(self.records.directory)
        fields(state, ('schema_version', 'operation', 'generation', 'envelope', 'policy', 'jobs'))
        if state['operation'] != 'memory_worker' or type(state['generation']) is not int or state['generation'] < 0:
            raise ValueError('Invalid memory worker record')
        if not isinstance(state['jobs'], dict):
            raise ValueError('Invalid job map')
        contract.validate(state['envelope'], state['policy'])
        return state

    def replace_host_state(self, *, envelope=None, policy=None):
        with self.records.lease():
            state = self.read()
            next_envelope = deepcopy(state['envelope'] if envelope is None else envelope)
            next_policy = deepcopy(state['policy'] if policy is None else policy)
            contract.validate(next_envelope, next_policy)
            state.update(envelope=next_envelope, policy=next_policy, generation=state['generation'] + 1)
            self.records.save(state)

    def inspect(self, job_id):
        job = self.read()['jobs'][job_id]
        if job['status'] == 'running':
            job['inspection_note'] = 'May still be active or interrupted. No automatic redispatch or recovery.'
        return job

    def claim(self, job_id, participant):
        contract.bounded_text(job_id, 'job ID', 128)
        from .memory_native import NativeParticipant
        if type(participant) not in (InjectedParticipant, NativeParticipant):
            raise ValueError('No qualified no-tools transport; use an explicit trusted injected participant')
        descriptor = participant.descriptor()
        with self.records.lease():
            state = self.read()
            if job_id in state['jobs']:
                raise ValueError('Job ID already claimed; inspect its receipt')
            policy, envelope = state['policy'], state['envelope']
            if type(participant) is NativeParticipant:
                participant.preflight(envelope, policy)
            if not {policy['routine_profile'], policy['stronger_profile']} <= set(descriptor['profiles']):
                raise ValueError('Participant does not supply the authorized profiles')
            route = policy['stronger_profile' if envelope['task_class'] == 'known_difficult' else 'routine_profile']
            job = dict(status='running', generation=state['generation'], envelope=deepcopy(envelope),
                       policy=deepcopy(policy), transport=descriptor, initial_profile=route,
                       sampled=sampled(job_id, policy), attempts=[], result=None, reason='')
            state['jobs'][job_id] = job
            self.records.save(state)
            return deepcopy(job)


def run(store, job_id, participant, *, authorize_job=None):
    """Claim once, call at most twice for reasoning and once for sampled review."""
    job = store.claim(job_id, participant)
    bound = job['envelope']['input']

    def call(role, profile, prompt, schema):
        with store.records.lease():
            state = store.read()
            check_current(state, job)
            if authorize_job is not None:
                try:
                    authorize_job(state['jobs'][job_id])
                except ValueError as error:
                    raise contract.StaleInput('Claimed job exceeds current host authority') from error
            if participant.descriptor() != job['transport']:
                raise contract.StaleInput('Participant profile changed')
            saved = state['jobs'][job_id]
            if saved['status'] != 'running' or len(saved['attempts']) >= 3:
                raise ValueError('Job stopped or call limit reached')
            index = len(saved['attempts'])
            saved['attempts'].append(dict(role=role, profile=profile, state='dispatched',
                                         prompt_digest=digest(prompt), schema_digest=digest(schema)))
            store.records.save(state)  # Durable intent precedes all participant activity.
        try:
            reply = deepcopy(participant(role, profile, deepcopy(prompt), deepcopy(schema)))
            native = job['transport']['transport'] == 'anthropic-data-v1'
            fields(reply, ('value', 'evidence') if native else ('value',))
            contract.bounded_json(reply, 4 * contract.OUTPUT_LIMIT if native else contract.OUTPUT_LIMIT)
        except Exception as error:
            with store.records.lease():
                state = store.read()
                saved = state['jobs'][job_id]
                failure = dict(state='unresolved', error=type(error).__name__)
                evidence = getattr(error, 'evidence', None)
                if evidence is not None:
                    contract.bounded_json(evidence, 4 * contract.OUTPUT_LIMIT)
                    failure['transport_evidence'] = deepcopy(evidence)
                saved['attempts'][index].update(failure)
                saved.update(status='unresolved', reason='Participant failed; no automatic retry')
                store.records.save(state)
            raise
        if not native:
            # Preserve the exact injected-v1 completed reply and subsequent stale
            # projection, including interrupted historical runs.
            with store.records.lease():
                state = store.read()
                state['jobs'][job_id]['attempts'][index].update(state='completed', reply=reply)
                store.records.save(state)
            check_current(store.read(), job)
            return reply['value']
        with store.records.lease():
            state = store.read()
            try:
                check_current(state, job)
                if participant.descriptor() != job['transport']:
                    raise contract.StaleInput('Participant profile changed after dispatch')
                if native:
                    from .memory_native import request_body, validate_evidence
                    body = request_body(role, profile, prompt, schema, job['transport']['config'])
                    if reply['evidence'].get('runtime_digest') != digest(job['transport']['runtime']):
                        raise ValueError('Native helper runtime differs from claimed descriptor')
                    if reply['evidence'].get('attempted_argv') != job['transport']['helper_argv']:
                        raise ValueError('Native helper command differs from claimed descriptor')
                    if validate_evidence(reply['evidence'], body) != reply['value']:
                        raise ValueError('Native reply differs from its raw provider evidence')
            except Exception as error:
                stale = (error if isinstance(error, contract.StaleInput) else
                         contract.StaleInput('Participant descriptor became unavailable after dispatch'))
                attempt = state['jobs'][job_id]['attempts'][index]
                attempt.update(state='unresolved', error=type(error).__name__)
                if native:
                    attempt['transport_evidence'] = deepcopy(reply['evidence'])
                state['jobs'][job_id].update(status='stale_stop', reason=str(stale))
                store.records.save(state)
                raise stale from error
            state['jobs'][job_id]['attempts'][index].update(state='completed', reply=reply)
            store.records.save(state)
        return reply['value']

    def assess(value):
        try:
            return dict(accepted=True, response=value, candidate=contract.normalize(bound, value))
        except (ValueError, KeyError, TypeError) as error:
            return dict(accepted=False, response=value, error=str(error))

    try:
        profile = job['initial_profile']
        first = assess(call('worker', profile, contract.prompt(bound), contract.schema_for(bound)))
        final = first
        escalated = False
        if (not first['accepted'] or first['response']['outcome'] == 'needs_reasoning') and profile != job['policy']['stronger_profile']:
            profile = job['policy']['stronger_profile']
            final = assess(call('escalation', profile, contract.prompt(bound, previous=first), contract.schema_for(bound)))
            escalated = True
        action = 'rejected'
        if final['accepted']:
            action = dict(update='proposal_ready', no_change='complete_no_change', needs_reasoning='unresolved_reasoning',
                          needs_evidence='await_evidence', needs_decision='await_decision')[final['response']['outcome']]
        result = dict(first=first, final=final, final_profile=profile, escalated=escalated, audit=None)
        if job['sampled'] and action in ('proposal_ready', 'complete_no_change', 'await_evidence', 'await_decision'):
            value = call('audit', job['policy']['stronger_profile'],
                         contract.prompt(bound, proposal=final['response']), contract.schema_for(bound, audit=True))
            try:
                contract.validate_audit(bound, value)
                result['audit'] = dict(state='completed', response=value)
                if value['verdict'] != 'supported':
                    action = 'quarantined'
            except (ValueError, KeyError, TypeError) as error:
                result['audit'] = dict(state='rejected', error=str(error))
                action = 'quarantined'
        with store.records.lease():
            state = store.read()
            check_current(state, job)
            state['jobs'][job_id].update(status=action, result=result)
            store.records.save(state)
    except (contract.StaleInput, FeatureUnavailable) as error:
        with store.records.lease():
            state = store.read()
            state['jobs'][job_id].update(status='stale_stop', reason=str(error))
            store.records.save(state)
    return store.inspect(job_id)


def validated_proposal(store, job_id):
    """Revalidate persisted results before a qualified adapter applies effects.

    Hold both store.records.lease() and the adapter's storage lock across this
    check and the effects. Otherwise this return value is only a snapshot.
    """
    state = store.read()
    job = state['jobs'][job_id]
    check_current(state, job)
    if job['status'] != 'proposal_ready':
        raise ValueError('Job does not have an applicable proposal')
    result = job['result']
    if not result['final']['accepted']:
        raise ValueError('Unaccepted result')
    validate_attempts(job)
    candidate = contract.normalize(job['envelope']['input'], result['final']['response'])
    if candidate != result['final']['candidate'] or result['final']['response']['outcome'] != 'update':
        raise ValueError('Persisted proposal was altered')
    if job['sampled'] != sampled(job_id, state['policy']):
        raise ValueError('Sample assignment was altered')
    if job['sampled']:
        audit = result['audit']
        if not audit or audit['state'] != 'completed':
            raise ValueError('Required semantic review missing')
        contract.validate_audit(job['envelope']['input'], audit['response'])
        if audit['response']['verdict'] != 'supported':
            raise ValueError('Semantic review did not support the proposal')
    return deepcopy(candidate)


def validate_attempts(job):
    """Bind the published result and audit to the durable dispatch/reply chain.

    These consistency checks detect altered derived fields. This is a local
    trusted journal, not cryptographic authentication against its filesystem owner.
    """
    result = job['result']
    bound = job['envelope']['input']
    policy = job['policy']
    initial = policy['stronger_profile' if job['envelope']['task_class'] == 'known_difficult' else 'routine_profile']
    if job['initial_profile'] != initial or type(result['escalated']) is not bool:
        raise ValueError('Altered initial route or escalation flag')
    first = result['first']
    try:
        first_candidate = contract.normalize(bound, first['response'])
        first_valid = True
    except (ValueError, KeyError, TypeError):
        first_candidate, first_valid = None, False
    if first['accepted'] is not first_valid or (first_valid and first['candidate'] != first_candidate):
        raise ValueError('Altered initial assessment')
    should_escalate = initial != policy['stronger_profile'] and (
        not first_valid or first['response']['outcome'] == 'needs_reasoning')
    if result['escalated'] != should_escalate:
        raise ValueError('Altered escalation route')
    expected = [('worker', initial, contract.prompt(bound), contract.schema_for(bound), first['response'])]
    if should_escalate:
        expected.append(('escalation', policy['stronger_profile'], contract.prompt(bound, previous=first),
                         contract.schema_for(bound), result['final']['response']))
    elif result['final'] != first:
        raise ValueError('Final result differs from the only worker assessment')
    if result['final_profile'] != expected[-1][1]:
        raise ValueError('Altered final profile')
    if job['sampled']:
        audit = result['audit']
        if not audit or audit['state'] != 'completed':
            raise ValueError('Required audit is missing')
        expected.append(('audit', policy['stronger_profile'],
                         contract.prompt(bound, proposal=result['final']['response']),
                         contract.schema_for(bound, audit=True), audit['response']))
    elif result['audit'] is not None:
        raise ValueError('Unexpected unsampled audit')
    if len(job['attempts']) != len(expected):
        raise ValueError('Altered attempt sequence')
    native = job['transport'].get('transport') == 'anthropic-data-v1'
    if native:
        from .memory_native import request_body, validate_descriptor, validate_evidence
        config = validate_descriptor(job['transport'])
    elif job['transport'] != dict(transport='trusted_injected_v1',
                                profiles=job['transport']['profiles'], tools=[]):
        raise ValueError('Unknown or altered worker transport descriptor')
    for saved, (role, profile, prompt, schema, response) in zip(job['attempts'], expected):
        reply = {'value': response}
        if native:
            evidence = saved.get('reply', {}).get('evidence')
            body = request_body(role, profile, prompt, schema, config)
            if evidence.get('runtime_digest') != digest(job['transport']['runtime']):
                raise ValueError('Native helper runtime differs from claimed descriptor')
            if evidence.get('attempted_argv') != job['transport']['helper_argv']:
                raise ValueError('Native helper command differs from claimed descriptor')
            if validate_evidence(evidence, body) != response:
                raise ValueError('Native evidence response differs from the published result')
            reply['evidence'] = evidence
        actual = dict(role=role, profile=profile, state='completed', prompt_digest=digest(prompt),
                      schema_digest=digest(schema), reply=reply)
        if saved != actual:
            raise ValueError('Published result is not bound to its completed attempt')
