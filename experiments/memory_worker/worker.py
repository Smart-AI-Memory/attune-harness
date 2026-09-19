"""Disposable proposal-only worker; persistent host policy, no memory effects."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'experiments/memory_citations'))
import citation_contract as contract
from baseline import old
from jsonschema import Draft202012Validator
from attune_harness.review_store import RunStore, read_record

ROUTES = {'routine': 'luna', 'known_difficult': 'astra'}
CAPABILITY = 'synthetic_facts_v1'


def validate(envelope, policy):
    """Validate host data before claiming a job or consuming a model call."""
    if not isinstance(envelope, dict) or set(envelope) != {'input', 'task_class', 'capability'}:
        raise ValueError('Expected input, task_class and capability')
    if not all(isinstance(envelope[k], str) and envelope[k].strip() for k in ('task_class', 'capability')):
        raise ValueError('Host class and capability must be named')
    bound = envelope['input']
    if not isinstance(bound, dict):
        raise ValueError('Input must be an object')
    fact_schema = contract.schema_for(bound)['properties']['facts']
    strings = dict(type='array', items=dict(type='string', minLength=1), maxItems=8, uniqueItems=True)
    schema = old.obj(dict(task=dict(type='string', minLength=1),
        record=old.obj(dict(version=dict(type='integer', minimum=0), facts=fact_schema)),
        sources=dict(type='array', minItems=1, maxItems=8,
            items=old.obj(dict(id=old.S, text=old.S, scope=old.S, context=old.S))),
        grants=old.obj({name: strings for name in ('scopes', 'kinds', 'create_ids', 'remove_ids', 'classify_ids')})))
    Draft202012Validator(schema).validate(bound)
    if not bound['task'].strip() or not set(bound['grants']['kinds']) <= set(old.KINDS):
        raise ValueError('Empty task or unsupported logical kinds')
    facts = bound['record']['facts']
    if len({f['id'] for f in facts}) != len(facts):
        raise ValueError('Captured fact IDs must be unique')
    sources = {s['id']: s for s in bound['sources']}
    for fact in facts:
        if any(not fact[k].strip() for k in ('id', 'text', 'scope')):
            raise ValueError('Captured fact fields must be nonempty')
        old.refs(bound, fact['source_ids'])
        if any(sources[id]['scope'] != fact['scope'] for id in fact['source_ids']):
            raise ValueError('Captured provenance crosses scope')
    if not isinstance(policy, dict) or set(policy) != {'sample_modulus', 'sample_bucket', 'sample_salt'}:
        raise ValueError('Expected explicit sampling policy')
    modulus, bucket = policy['sample_modulus'], policy['sample_bucket']
    if type(modulus) is not int or type(bucket) is not int or not 1 <= modulus <= 10000 or not 0 <= bucket < modulus:
        raise ValueError('Invalid sampling bucket/modulus')
    if not isinstance(policy['sample_salt'], str) or not policy['sample_salt'].strip():
        raise ValueError('Sampling salt must be explicit')


def sampled(job_id, policy):
    value = (policy['sample_salt'] + ':' + job_id).encode('utf-8')
    return int.from_bytes(hashlib.sha256(value).digest(), 'big') % policy['sample_modulus'] == policy['sample_bucket']


class WorkerStore:
    """Job artifacts only. Explicit new directory; no default memory location."""
    def __init__(self, directory):
        self.records = RunStore(Path(directory), existing=True)

    @classmethod
    def create(cls, directory, envelope, policy):
        validate(envelope, policy)
        records = RunStore(Path(directory))
        with records.lease():
            records.save(dict(schema_version=1, generation=0, envelope=deepcopy(envelope),
                              policy=deepcopy(policy), jobs={}))
        return cls(directory)

    def read(self):
        return read_record(self.records.directory)

    def replace_host_state(self, *, envelope=None, policy=None):
        """Trusted host update; generation prevents change-and-restore reuse."""
        with self.records.lease():
            state = self.read()
            next_envelope = deepcopy(state['envelope'] if envelope is None else envelope)
            next_policy = deepcopy(state['policy'] if policy is None else policy)
            validate(next_envelope, next_policy)
            state.update(envelope=next_envelope, policy=next_policy, generation=state['generation'] + 1)
            self.records.save(state)

    def inspect(self, job_id):
        job = self.read()['jobs'][job_id]
        if job['status'] == 'running':
            job['inspection_note'] = 'May still be active or interrupted. No automatic redispatch or recovery.'
        return job

    def claim(self, job_id):
        if not isinstance(job_id, str) or not job_id.strip() or len(job_id) > 128:
            raise ValueError('Host job ID must be nonempty and at most 128 characters')
        with self.records.lease():
            state = self.read()
            validate(state['envelope'], state['policy'])
            if job_id in state['jobs']:
                raise ValueError('Job ID already claimed; inspect its existing receipt')
            envelope = state['envelope']
            route = ROUTES.get(envelope['task_class'])
            supported = envelope['capability'] == CAPABILITY and route is not None
            job = dict(status='running' if supported else 'blocked', generation=state['generation'],
                envelope=deepcopy(envelope), policy=deepcopy(state['policy']), initial_model=route,
                sampled=sampled(job_id, state['policy']), attempts=[], result=None,
                reason='' if supported else 'Unsupported host capability or task class; no participant called')
            state['jobs'][job_id] = job
            self.records.save(state)
            return deepcopy(job)


def check_current(state, job):
    if any(state[k] != job[k] for k in ('generation', 'envelope', 'policy')):
        raise old.StaleInput('Host input, routing, policy or generation changed')


def run(store, job_id, participant):
    """One claim, one initial worker, at most one escalation and one audit."""
    job = store.claim(job_id)
    if job['status'] != 'running':
        return store.inspect(job_id)
    bound = deepcopy(job['envelope']['input'])
    bound['grants']['assigned_model'] = job['initial_model']
    case = {'input': bound}

    def current():
        check_current(store.read(), job)
        return deepcopy(bound)

    def call(role, model, prompt, schema):
        with store.records.lease():
            state = store.read()
            check_current(state, job)
            saved = state['jobs'][job_id]
            if saved['status'] != 'running' or len(saved['attempts']) >= 3:
                raise ValueError('Job no longer running or call limit reached')
            index = len(saved['attempts'])
            saved['attempts'].append(dict(role=role, model=model, state='dispatched',
                prompt=deepcopy(prompt), schema=deepcopy(schema)))
            store.records.save(state)  # Dispatch intent must persist before callback.
        try:
            reply = deepcopy(participant(role, model, deepcopy(prompt), deepcopy(schema)))
            if not isinstance(reply, dict) or 'value' not in reply:
                raise ValueError('Participant transport did not return a value envelope')
        except Exception as error:
            with store.records.lease():
                state = store.read()
                saved = state['jobs'][job_id]
                saved['attempts'][index].update(state='unresolved', error=str(error))
                saved.update(status='unresolved', reason='Participant failed; no retry')
                store.records.save(state)
            raise
        with store.records.lease():
            state = store.read()
            state['jobs'][job_id]['attempts'][index].update(state='completed', reply=reply)
            store.records.save(state)
        return reply

    try:
        result = contract.execute(case, 'repaired', call, current)
        if job['sampled'] and result['action'] in ('proposal_ready', 'complete_no_change', 'await_evidence', 'await_decision'):
            result['audit'] = contract.audit(case, result, call, current)
        with store.records.lease():
            state = store.read()
            check_current(state, job)
            saved = state['jobs'][job_id]
            if saved['status'] != 'running':
                return store.inspect(job_id)  # A caught audit transport error remains unresolved.
            saved.update(status=result['action'], result=deepcopy(result))
            store.records.save(state)
    except old.StaleInput as error:
        with store.records.lease():
            state = store.read()
            state['jobs'][job_id].update(status='stale_stop', reason=str(error))
            store.records.save(state)
    except Exception:
        # Preserve uncertain intent/replies. Never retry a participant because publication failed.
        raise
    return store.inspect(job_id)
